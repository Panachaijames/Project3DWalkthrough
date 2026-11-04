"""An interpreter for the small, conservative subset of MAXScript that the generated Max scripts use, over a mock 3ds Max.

3ds Max is not installed on this machine, so the tests of furniture_max.py RUN the generated functions here: command-style calls with
keyword arguments, if / for, blocks, arrays, point and matrix values, user properties, layers, a Box with a transform. Logic slips
(a wrong index, a name that is never set, a string added to a number, a call with a missing argument) show up as MaxError.

What this does NOT prove: it knows about 3ds Max only what is written in this file (the mock below). It shows that the script does
what its author meant under that reading of Max; whether Max agrees is for the 3D team's run.  The mock's reading, with the source:
  * matrix3 <row1> <row2> <row3> <row4>; rows 1-3 are the node's X, Y, Z axes, row 4 its position, a point is a row vector: p * tm
    (Autodesk MAXScript help "Matrix3 Values", "How do I rotate a vector around the Z axis?" (theV * rm); Max SDK Matrix3 "all vectors
    are assumed to be row vectors"; "Using Node Transform Properties": a node turned +35 degrees about Z has transform
    matrix3 [0.819152,0.573576,0] [-0.573576,0.819152,0] [0,0,1] [x,y,z]);
  * a Box has its pivot in the middle of its base: its local vertex 1 is [-w/2,-l/2,0] (same page: a 25 x 25 x 25 box gives
    [-12.5,-12.5,0]); width runs along local X, length along Y, height along Z (Box : GeometryClass, in world units);
  * node.min / node.max: the world bounding box of the node (the docs only say "bounding box"; here: of its 8 corners in the world).
    The docs do not say what they return for a node that is turned, a quarter turn included, so a test can change it for such a node
    only: scene.bbox_error_turned makes it wrong by a given amount, scene.bbox_unturned gives the other reading (the extents of the
    box as if it were not turned). A script must not depend on either;
  * getUserProp reads the stored text as a number, else a boolean, else a string (help: "MAXScript tries to convert the property
    value to a number, if that fails then to a boolean ... otherwise a text string"); setUserProp stores the string form. The help
    gives no value for empty text, and none for the word none either: here both read as the text, unless a test sets
    scene.empty_prop_is_undefined / scene.none_is_undefined (then undefined), and a script must work either way;
  * LayerManager.getLayerFromName gives undefined when there is no such layer (relied on by the shipped scripts);
    layer.addNode moves a node to the layer (LayerProperties interface).
Arrays are 1-based and every out-of-range index is an error here (stricter than Max, on purpose).
"""
import fnmatch, math, re
from maxscript_lite import Tok, tokenize, structure


class MaxError(Exception): pass


class Return(Exception):
    def __init__(self, value): self.value = value


class Sym(str):
    def __eq__(self, o): return isinstance(o, Sym) and str.lower(self) == str.lower(o)
    def __ne__(self, o): return not self.__eq__(o)
    def __hash__(self): return hash(str.lower(self))


class Cls:                                 # a class value (Box, Extrude ...)
    def __init__(self, name): self.name = name
    def __repr__(self): return f'<class {self.name}>'


class P:                                   # Point2 / Point3
    def __init__(self, *v): self.v = [float(a) for a in v]
    def copy(self): return P(*self.v)
    def __repr__(self): return '[' + ','.join(f'{a:g}' for a in self.v) + ']'


class M3:                                  # matrix3: four rows
    def __init__(self, r1, r2, r3, r4): self.rows = [r1.copy(), r2.copy(), r3.copy(), r4.copy()]
    def copy(self): return M3(*self.rows)
    def __repr__(self): return 'matrix3 ' + ' '.join(repr(r) for r in self.rows)


class Color:
    def __init__(self, r, g, b): self.v = (r, g, b)
    def __eq__(self, o): return isinstance(o, Color) and self.v == o.v
    def __repr__(self): return f'(color {self.v[0]} {self.v[1]} {self.v[2]})'


class Mat:
    def __init__(self, name, diffuse): self.name, self.diffuse = name, diffuse


class Layer:
    def __init__(self, name): self.name, self.nodes = name, []
    def add(self, node):
        if node.layer is not None: node.layer.nodes.remove(node)
        node.layer = self; self.nodes.append(node)


def mul_pm(p, m):                          # point * matrix3: row vector times matrix, row 4 is the translation
    return P(*[sum(p.v[i] * m.rows[i].v[j] for i in range(3)) + m.rows[3].v[j] for j in range(3)])


class Node:
    def __init__(self, scene, cls, name, **params):
        self.scene, self.cls, self.name, self.params = scene, cls, name, params
        self.tm = M3(P(1, 0, 0), P(0, 1, 0), P(0, 0, 1), P(0, 0, 0))
        self.props, self.layer, self.material, self.wirecolor, self.modifiers, self.flags = {}, None, None, Color(0, 0, 0), [], {}
        scene.objects.append(self)
        scene.layer('0').add(self)

    def corners(self):                     # the 8 corners of a Box in the world (pivot in the middle of the base)
        w, l, h = self.params['width'], self.params['length'], self.params['height']
        return [mul_pm(P(x, y, z), self.tm) for x in (-w / 2, w / 2) for y in (-l / 2, l / 2) for z in (0.0, h)]

    def corners_unturned(self):            # the 8 corners of the Box as if it were not turned: its pivot, width, length and height only
        w, l, h = self.params['width'], self.params['length'], self.params['height']
        px, py, pz = self.tm.rows[3].v
        return [P(px + x, py + y, pz + z) for x in (-w / 2, w / 2) for y in (-l / 2, l / 2) for z in (0.0, h)]

    def unrotated(self):                   # not turned about Z at all (its X axis is +x): min / max are then certainly its own extents
        x, y = self.tm.rows[0].v[0], self.tm.rows[0].v[1]
        return abs(y) < 1e-5 and x > 0


class Scene:
    """The mock scene: nodes, layers, units, and a record of what the script asked for."""
    def __init__(self):
        self.objects, self.layers, self.messages, self.listener, self.converted = [], {}, [], [], []
        self.units = {'systemtype': Sym('meters'), 'systemscale': 1.0, 'displaytype': Sym('metric'), 'metrictype': Sym('meters')}
        self.bbox_error = None             # {'min' or 'max': {axis: delta}}: the mock Max reports a wrong bounding box (drives the failure paths)
        self.bbox_error_turned = None      # the same, but only for a box that is turned at all, a quarter turn included (what Max reports
                                           # for such a node is not documented: a script must not depend on it)
        self.bbox_unturned = False         # a turned node reports the extents of its box as if it were not turned (the other possible reading)
        self.empty_prop_is_undefined = False   # getUserProp has no documented value for empty text: undefined here when True, else ""
        self.none_is_undefined = False         # ... and the word none, which Autodesk does not mention either: undefined when True, else the text
        self.layer('0')

    def layer(self, name):
        if name.lower() not in self.layers: self.layers[name.lower()] = Layer(name)
        return self.layers[name.lower()]


def tostr(v):
    if v is None: return 'undefined'
    if v is True: return 'true'
    if v is False: return 'false'
    if isinstance(v, float):
        s = f'{v:.6g}'
        return s if ('.' in s or 'e' in s or 'n' in s) else s + '.0'
    if isinstance(v, list): return '#(' + ', '.join(tostr(a) if not isinstance(a, str) else '"' + a + '"' for a in v) + ')'
    return str(v)


def eq(a, b):
    if isinstance(a, bool) or isinstance(b, bool): return a is b
    if isinstance(a, Sym) or isinstance(b, Sym): return isinstance(a, Sym) and isinstance(b, Sym) and a == b
    if isinstance(a, str) and isinstance(b, str): return a.lower() == b.lower()
    if isinstance(a, (int, float)) and isinstance(b, (int, float)): return a == b
    if a is None or b is None: return a is b
    return a is b


def num_check(v, what):
    if isinstance(v, bool) or not isinstance(v, (int, float)): raise MaxError(f'{what}: expected a number, got {tostr(v)!r}')
    return v


BOOLWORDS = {'true': True, 'false': False, 'undefined': None, 'ok': None}
STOP = {'then', 'do', 'else', 'of', 'where', 'and', 'or', 'to', 'by', 'in', 'as', 'collect', 'catch', 'not'}
BUILTIN_ARITY = {'append': 2, 'finditem': 2, 'floor': 1, 'abs': 1, 'getuserprop': 2, 'setuserprop': 3, 'classof': 1, 'matchpattern': 1,
                 'messagebox': 1, 'format': -1, 'timestamp': 0, 'standardmaterial': 0, 'color': 3, 'matrix3': 4, 'converttomesh': 1,
                 'select': 1, 'clearselection': 0, 'redrawviews': 0, 'destroydialog': 1, 'getcurrentexception': 0, 'max': -2}
CTORS = {'box', 'point'}                   # a class value; a constructor call when keyword arguments follow
METHOD_ARITY = {'addnode': 1, 'getlayerfromname': 1, 'newlayerfromname': 1, 'settype': 1}


class Parser:
    def __init__(self, toks, arity):
        self.t, self.i, self.arity = toks, 0, arity            # arity(name): positional arguments, -1 variadic, None if not a function

    def peek(self, k=0): return self.t[self.i + k] if self.i + k < len(self.t) else Tok('eof', '', 0, 0, False)
    def next(self): t = self.peek(); self.i += 1; return t
    def is_id(self, t, *w): return t.kind == 'id' and t.text.lower() in w
    def is_op(self, t, *w): return t.kind == 'op' and t.text in w
    def err(self, msg): raise MaxError(f'parse error at line {self.peek().line}: {msg} (near {self.peek().text!r})')

    def skip_nl(self):
        while self.peek().kind == 'nl' or self.is_op(self.peek(), ';'): self.i += 1

    def block_body(self):                  # statements up to the closing bracket, which is consumed
        stmts = []
        self.skip_nl()
        while not (self.peek().kind == 'close' and self.peek().text == ')'):
            if self.peek().kind == 'eof': self.err('unclosed block')
            stmts.append(self.stmt()); self.skip_nl()
        self.i += 1
        return ('block', stmts)

    def stmt(self):
        t = self.peek()
        if self.is_id(t, 'local', 'global'):
            self.i += 1; name = self.next().text; init = None
            if self.is_op(self.peek(), '='): self.i += 1; init = self.expr()
            return (t.text.lower(), name, init)
        if self.is_id(t, 'return'):
            self.i += 1
            nxt = self.peek()
            return ('return', None if nxt.kind in ('nl', 'close', 'eof') or self.is_op(nxt, ';') else self.expr())
        e = self.expr()
        if self.is_op(self.peek(), '=', '+=', '-=', '*=', '/='):
            op = self.next().text
            if e[0] not in ('var', 'prop', 'index'): self.err('cannot assign to that')
            return ('assign', e, op, self.expr())
        return e

    def expr(self): return self.or_()

    def or_(self):
        l = self.and_()
        while self.is_id(self.peek(), 'or'): self.i += 1; l = ('or', l, self.and_())
        return l

    def and_(self):
        l = self.not_()
        while self.is_id(self.peek(), 'and'): self.i += 1; l = ('and', l, self.not_())
        return l

    def not_(self):
        if self.is_id(self.peek(), 'not'): self.i += 1; return ('not', self.not_())
        return self.cmp()

    def cmp(self):
        l = self.add()
        while self.is_op(self.peek(), '==', '!=', '<', '>', '<=', '>='): op = self.next().text; l = ('bin', op, l, self.add())
        return l

    def add(self):
        l = self.mul()
        while self.is_op(self.peek(), '+', '-'): op = self.next().text; l = ('bin', op, l, self.mul())
        return l

    def mul(self):
        l = self.unary()
        while self.is_op(self.peek(), '*', '/'): op = self.next().text; l = ('bin', op, l, self.unary())
        return l

    def unary(self):
        if self.is_op(self.peek(), '-'): self.i += 1; return ('neg', self.unary())
        e = self.postfix(True)
        while self.is_id(self.peek(), 'as'): self.i += 1; e = ('as', e, self.next().text.lower())
        return e

    def starts_operand(self, t):
        return t.kind in ('num', 'str', 'sym', 'open') or (t.kind == 'id' and t.text.lower() not in STOP)

    def operand(self): return self.postfix(False)      # one command-call argument: a primary with its postfix parts, no operators

    def postfix(self, calls):
        e = self.primary(calls)
        while True:
            t = self.peek()
            if self.is_op(t, '.') and not t.space:
                self.i += 1; name = self.next().text.lower()
                if name in METHOD_ARITY: e = ('mcall', e, name, [self.operand() for _ in range(METHOD_ARITY[name])])
                else: e = ('prop', e, name)
            elif t.kind == 'open' and t.text == '[' and not t.space:
                self.i += 1; idx = self.expr()
                if not (self.peek().kind == 'close' and self.peek().text == ']'): self.err('expected ]')
                self.i += 1; e = ('index', e, idx)
            else: return e

    def primary(self, calls):
        t = self.next()
        if t.kind == 'num': return ('lit', float(t.text) if ('.' in t.text or 'e' in t.text.lower()) else int(t.text))
        if t.kind == 'str': return ('lit', unescape(t.text[1:-1]))
        if t.kind == 'sym': return ('lit', Sym(t.text[1:]))
        if t.kind == 'open' and t.text == '(': return self.block_body()
        if t.kind == 'open' and t.text == '#(':
            items = []
            self.skip_nl()
            while self.peek().kind != 'close':
                items.append(self.expr()); self.skip_nl()
                if self.is_op(self.peek(), ','): self.i += 1; self.skip_nl()
            self.i += 1
            return ('list', items)
        if t.kind == 'open' and t.text == '[':
            items = [self.expr()]
            while self.is_op(self.peek(), ','): self.i += 1; items.append(self.expr())
            if not (self.peek().kind == 'close' and self.peek().text == ']'): self.err('expected ]')
            self.i += 1
            if len(items) not in (2, 3): self.err('a point has 2 or 3 numbers')
            return ('pt', items)
        if t.kind == 'id':
            w = t.text.lower()
            if w in BOOLWORDS: return ('lit', BOOLWORDS[w])
            if w == 'if': return self.if_()
            if w == 'for': return self.for_()
            if w in ('fn', 'try', 'case', 'while', 'on', 'rollout'): self.err(f'{w} is not supported by the mock interpreter')
            ar = self.arity(w)
            if ar is not None and calls: return self.call(w, ar)
            return ('var', w)
        self.err(f'unexpected {t.text!r}')

    def kw_next(self):
        return self.peek().kind == 'id' and self.is_op(self.peek(1), ':') and not self.peek(1).space

    def call(self, w, ar):
        if w == 'max':                     # max zoomext sel all: a command made of words
            while self.peek().kind not in ('nl', 'close', 'eof'): self.i += 1
            return ('lit', None)
        args, kw = [], {}
        if ar == 0 and self.peek().kind == 'open' and self.peek().text == '(' and self.peek(1).kind == 'close':
            self.i += 2; return ('call', w, [], {})
        if w in CTORS and not self.kw_next(): return ('var', w)                  # the class itself (classOf o != Box)
        while True:
            if self.kw_next():
                name = self.next().text.lower(); self.i += 1; kw[name] = self.operand(); continue
            if ar >= 0 and len(args) >= ar: break
            if not self.starts_operand(self.peek()): break
            args.append(self.operand())
        if ar > 0 and len(args) != ar: self.err(f'{w} wants {ar} arguments, found {len(args)}')
        return ('call', w, args, kw)

    def if_(self):
        cond = self.expr()
        if not self.is_id(self.peek(), 'then', 'do'): self.err('expected then / do')
        self.i += 1; self.skip_nl()
        then = self.stmt()
        j = self.i
        self.skip_nl()
        if self.is_id(self.peek(), 'else'):
            self.i += 1; self.skip_nl()
            return ('if', cond, then, self.stmt())
        self.i = j
        return ('if', cond, then, None)

    def for_(self):
        var = self.next().text.lower()
        coll = a = b = step = where = None
        if self.is_id(self.peek(), 'in'): self.i += 1; coll = self.expr()
        elif self.is_op(self.peek(), '='):
            self.i += 1; a = self.expr()
            if not self.is_id(self.peek(), 'to'): self.err('expected to')
            self.i += 1; b = self.expr()
            if self.is_id(self.peek(), 'by'): self.i += 1; step = self.expr()
        else: self.err('for needs in or =')
        if self.is_id(self.peek(), 'where'): self.i += 1; where = self.expr()
        if not self.is_id(self.peek(), 'do', 'collect'): self.err('expected do')
        self.i += 1; self.skip_nl()
        return ('for', var, coll, a, b, step, where, self.stmt())


def unescape(s):
    return re.sub(r'\\(.)', lambda m: {'n': '\n', 't': '\t', '"': '"', '\\': '\\'}.get(m.group(1), m.group(1)), s)


class Env:
    def __init__(self, parent=None): self.vars, self.parent = {}, parent

    def find(self, name):
        e = self
        while e:
            if name in e.vars: return e
            e = e.parent
        return None


class ObjectSet:
    def __init__(self, scene): self.scene = scene
    def items(self): return self.scene.objects


class UnitsObj:
    def __init__(self, scene): self.scene = scene


class LayerManagerObj:
    def __init__(self, scene): self.scene = scene


class ViewportObj: pass


class Control:                             # a rollout control: a spinner has a value, a checkbox a state
    def __init__(self, value=0, checked=False): self.value, self.checked = value, checked


class Interp:
    """Loads the global lines and the functions of a script (rollouts and the rest are skipped) and runs them on a mock Max."""
    def __init__(self, text, scene=None):
        self.scene = scene or Scene()
        self.g = Env()
        self.fns, self.py = {}, {}         # user functions: name -> [params, tokens, tree]; Python overrides: name -> callable
        for name in ('Box', 'Point', 'Extrude', 'Smooth', 'SplineShape', 'EditableMesh', 'Integer', 'Float', 'String'): self.g.vars[name.lower()] = Cls(name)
        self.g.vars['objects'] = ObjectSet(self.scene)
        self.g.vars['units'] = UnitsObj(self.scene)
        self.g.vars['layermanager'] = LayerManagerObj(self.scene)
        self.g.vars['viewport'] = ViewportObj()
        self.load(text)

    def load(self, text):
        toks, errs = tokenize(text)
        match, depth, e2 = structure(toks)
        if errs or e2: raise MaxError(f'cannot load: {(errs + e2)[:3]}')
        n, i = len(toks), 0
        while i < n:
            t = toks[i]
            if depth[i] == 0 and t.kind == 'id' and t.text.lower() in ('fn', 'rollout'):
                j = i + 1
                while j < n and not (toks[j].kind == 'open' and depth[j] == 0): j += 1
                if t.text.lower() == 'fn':
                    k, params = i + 2, []
                    while not (toks[k].kind == 'op' and toks[k].text == '='): params.append(toks[k].text.lower()); k += 1
                    self.fns[toks[i + 1].text.lower()] = [params, toks[j:match[j] + 1], None]
                i = match[j] + 1
            elif depth[i] == 0 and t.kind == 'id' and t.text.lower() == 'global':
                j = i + 1
                while j < n and toks[j].kind != 'nl': j += 1
                self.ev(Parser(toks[i:j], self.arity).stmt(), Env(self.g))
                i = j
            else: i += 1

    def arity(self, name):
        if name in self.fns: return len(self.fns[name][0])
        if name in BUILTIN_ARITY: return BUILTIN_ARITY[name]
        if name in CTORS: return 0
        return None

    def override(self, name, pyfunc): self.py[name.lower()] = pyfunc      # replace a script function by Python (for template parts not under test)
    def get(self, name): return self.g.vars[name.lower()]
    def set(self, name, value): self.g.vars[name.lower()] = value

    def run(self, text, **variables):
        """Run statements (a fragment of a script) in a fresh frame that holds `variables`; returns the last value."""
        toks, errs = tokenize('(\n' + text + '\n)')
        if errs: raise MaxError(f'cannot read: {errs[:2]}')
        env = Env(self.g)
        for k, v in variables.items(): env.vars[k.lower()] = v
        try: return self.ev(Parser(toks, self.arity).primary(False), env)
        except Return as r: return r.value

    def call(self, name, *args, **kw): return self.call_fn(name.lower(), list(args), {k.lower(): v for k, v in kw.items()})

    def call_fn(self, name, args, kw):
        if name in self.py: return self.py[name](self, *args, **kw)
        if name in self.fns:
            params, toks, tree = self.fns[name]
            if len(args) != len(params): raise MaxError(f'{name} takes {len(params)} arguments, got {len(args)}')
            if tree is None: tree = self.fns[name][2] = Parser(toks, self.arity).primary(False)
            env = Env(self.g)
            env.vars.update(zip(params, args))
            try: return self.ev(tree, env)
            except Return as r: return r.value
        if name in BUILTINS: return BUILTINS[name](self, *args, **kw)
        raise MaxError(f'unknown function {name}')

    def lookup(self, name, env):
        e = env.find(name)
        if e is None: raise MaxError(f'unknown variable {name}')
        return e.vars[name]

    def ev(self, n, env):
        k = n[0]
        if k == 'lit': return n[1]
        if k == 'var': return self.lookup(n[1], env)
        if k == 'block':
            v = None
            for s in n[1]: v = self.ev(s, env)
            return v
        if k == 'local': env.vars[n[1].lower()] = self.ev(n[2], env) if n[2] is not None else None; return None
        if k == 'global': self.g.vars[n[1].lower()] = self.ev(n[2], env) if n[2] is not None else None; return None
        if k == 'list': return [self.ev(e, env) for e in n[1]]
        if k == 'pt': return P(*[num_check(self.ev(e, env), 'point') for e in n[1]])
        if k == 'neg': return -num_check(self.ev(n[1], env), 'minus')
        if k == 'not':
            v = self.ev(n[1], env)
            if not isinstance(v, bool): raise MaxError('not needs a boolean')
            return not v
        if k in ('and', 'or'):
            l = self.ev(n[1], env)
            if not isinstance(l, bool): raise MaxError(f'{k} needs booleans, got {tostr(l)}')
            if (k == 'and' and not l) or (k == 'or' and l): return l
            r = self.ev(n[2], env)
            if not isinstance(r, bool): raise MaxError(f'{k} needs booleans, got {tostr(r)}')
            return r
        if k == 'bin': return self.binop(n[1], self.ev(n[2], env), self.ev(n[3], env))
        if k == 'as': return self.convert(self.ev(n[1], env), n[2])
        if k == 'prop': return getprop(self.ev(n[1], env), n[2])
        if k == 'index':
            a, i = self.ev(n[1], env), self.ev(n[2], env)
            if isinstance(a, ObjectSet): a = a.items()
            if not isinstance(a, list): raise MaxError('indexing something that is not an array')
            if isinstance(i, bool) or not isinstance(i, int) or not 1 <= i <= len(a): raise MaxError(f'array index out of range: {tostr(i)} of {len(a)}')
            return a[i - 1]
        if k == 'call':
            return self.call_fn(n[1], [self.ev(a, env) for a in n[2]], {a: self.ev(v, env) for a, v in n[3].items()})
        if k == 'mcall': return callmethod(self.ev(n[1], env), n[2], [self.ev(a, env) for a in n[3]])
        if k == 'if':
            c = self.ev(n[1], env)
            if not isinstance(c, bool): raise MaxError(f'if needs a boolean, got {tostr(c)}')
            if c: return self.ev(n[2], env)
            return self.ev(n[3], env) if n[3] is not None else None
        if k == 'for': return self.for_loop(n, env)
        if k == 'return': raise Return(self.ev(n[1], env) if n[1] is not None else None)
        if k == 'assign':
            _, target, op, rhs = n
            val = self.ev(rhs, env)
            if op != '=': val = self.binop(op[0], self.ev(target, env), val)
            self.store(target, val, env)
            return val
        raise MaxError(f'cannot evaluate {k}')

    def for_loop(self, n, env):
        _, var, coll, a, b, step, where, body = n
        if coll is not None:
            c = self.ev(coll, env)
            seq = list(c.items()) if isinstance(c, ObjectSet) else list(c)
        else:
            lo, hi, st = self.ev(a, env), self.ev(b, env), (self.ev(step, env) if step is not None else 1)
            seq = list(range(lo, hi + 1, st)) if st > 0 else list(range(lo, hi - 1, st))
        v = None
        for item in seq:
            env.vars[var] = item
            if where is not None:
                w = self.ev(where, env)
                if not isinstance(w, bool): raise MaxError('where needs a boolean')
                if not w: continue
            v = self.ev(body, env)
        return v

    def store(self, target, val, env):
        k = target[0]
        if k == 'var':
            e = env.find(target[1])
            if e is None: raise MaxError(f'assignment to {target[1]}, which is declared nowhere (local or global)')
            e.vars[target[1]] = val
        elif k == 'prop':
            obj = self.ev(target[1], env)
            if isinstance(obj, (P, M3)):                               # a value type: change a copy, then store it back
                obj = obj.copy(); setprop(obj, target[2], val); self.store(target[1], obj, env)
            else: setprop(obj, target[2], val)
        elif k == 'index':
            a, i = self.ev(target[1], env), self.ev(target[2], env)
            if not isinstance(a, list) or isinstance(i, bool) or not isinstance(i, int) or not 1 <= i <= len(a): raise MaxError(f'array index out of range: {tostr(i)}')
            a[i - 1] = val

    def binop(self, op, a, b):
        if op == '+':
            if isinstance(a, str) and isinstance(b, str) and not isinstance(a, Sym): return a + b
            if isinstance(a, P) and isinstance(b, P): return P(*[x + y for x, y in zip(a.v, b.v)])
            return num_check(a, '+') + num_check(b, '+')
        if op == '-':
            if isinstance(a, P) and isinstance(b, P): return P(*[x - y for x, y in zip(a.v, b.v)])
            return num_check(a, '-') - num_check(b, '-')
        if op == '*':
            if isinstance(a, P) and isinstance(b, M3): return mul_pm(a, b)
            if isinstance(a, P): return P(*[x * num_check(b, '*') for x in a.v])
            return num_check(a, '*') * num_check(b, '*')
        if op == '/':
            a, b = num_check(a, '/'), num_check(b, '/')
            return int(a / b) if isinstance(a, int) and isinstance(b, int) else a / b          # integer division, as MAXScript
        if op == '==': return eq(a, b)
        if op == '!=': return not eq(a, b)
        a, b = num_check(a, op), num_check(b, op)
        return {'<': a < b, '>': a > b, '<=': a <= b, '>=': a >= b}[op]

    def convert(self, v, cls):
        if cls == 'string': return str(v) if isinstance(v, str) else tostr(v)
        if cls == 'float':
            if isinstance(v, str):
                try: return float(v)
                except ValueError: raise MaxError(f'{v!r} as float')
            return float(num_check(v, 'as float'))
        if cls == 'integer':
            if isinstance(v, str):
                try: return int(float(v))
                except ValueError: raise MaxError(f'{v!r} as integer')
            return int(num_check(v, 'as integer'))
        raise MaxError(f'as {cls}')


def getprop(obj, name):
    if isinstance(obj, list) and name == 'count': return len(obj)
    if isinstance(obj, ObjectSet) and name == 'count': return len(obj.scene.objects)
    if isinstance(obj, P) and name in ('x', 'y', 'z'):
        i = 'xyz'.index(name)
        if i >= len(obj.v): raise MaxError(f'point has no {name}')
        return obj.v[i]
    if isinstance(obj, M3):
        if name in ('row1', 'row2', 'row3', 'row4'): return obj.rows['1234'.index(name[3])].copy()
        if name == 'translation': return obj.rows[3].copy()
    if isinstance(obj, UnitsObj) and name in obj.scene.units: return obj.scene.units[name]
    if isinstance(obj, Layer) and name == 'name': return obj.name
    if isinstance(obj, Mat) and name in ('name', 'diffuse'): return getattr(obj, name)
    if isinstance(obj, Control) and name in ('value', 'checked'): return getattr(obj, name)
    if isinstance(obj, Node):
        if name == 'name': return obj.name
        if name == 'pos': return obj.tm.rows[3].copy()
        if name == 'transform': return obj.tm.copy()
        if name == 'layer': return obj.layer
        if name == 'material': return obj.material
        if name == 'wirecolor': return obj.wirecolor
        if name == 'modifiers': return obj.modifiers
        if name in obj.params: return obj.params[name]
        if name in ('min', 'max') and obj.cls.name == 'Box':
            turned = not obj.unrotated()
            cs = obj.corners_unturned() if turned and obj.scene.bbox_unturned else obj.corners()
            r = P(*[(min if name == 'min' else max)(c.v[i] for c in cs) for i in range(3)])
            for axis, delta in (obj.scene.bbox_error or {}).get(name, {}).items(): r.v['xyz'.index(axis)] += delta       # drives the failure paths
            if turned:
                for axis, delta in (obj.scene.bbox_error_turned or {}).get(name, {}).items(): r.v['xyz'.index(axis)] += delta
            return r
        if name in obj.flags: return obj.flags[name]
    raise MaxError(f'{type(obj).__name__} has no property {name}')


def setprop(obj, name, val):
    if isinstance(obj, P) and name in ('x', 'y', 'z'): obj.v['xyz'.index(name)] = float(num_check(val, name)); return
    if isinstance(obj, M3) and name in ('row1', 'row2', 'row3', 'row4'): obj.rows['1234'.index(name[3])] = val.copy(); return
    if isinstance(obj, UnitsObj) and name in obj.scene.units: obj.scene.units[name] = val; return
    if isinstance(obj, Node):
        if name == 'name': obj.name = val; return
        if name == 'pos': obj.tm.rows[3] = P(*val.v[:3]); return
        if name == 'transform':
            if not isinstance(val, M3): raise MaxError('transform needs a matrix3')
            obj.tm = val.copy(); return
        if name == 'material': obj.material = val; return
        if name == 'wirecolor': obj.wirecolor = val; return
        if name in obj.params and obj.cls.name == 'Box': obj.params[name] = float(num_check(val, name)); return
        if name in ('ishidden', 'ignoreextents'): obj.flags[name] = val; return
    raise MaxError(f'cannot set {name} on {type(obj).__name__}')


def callmethod(obj, name, args):
    if name == 'addnode' and isinstance(obj, Layer):
        if not isinstance(args[0], Node): raise MaxError('addNode needs a node')
        obj.add(args[0]); return None
    if isinstance(obj, LayerManagerObj) and name in ('getlayerfromname', 'newlayerfromname'):
        key = args[0].lower()
        if name == 'getlayerfromname': return obj.scene.layers.get(key)
        return obj.scene.layers[key] if key in obj.scene.layers else obj.scene.layer(args[0])
    if isinstance(obj, ViewportObj) and name == 'settype': return None
    raise MaxError(f'no method {name} on {type(obj).__name__}')


# ---- the builtin functions of the mock --------------------------------------------------------------------------------------

def _getuserprop(it, node, key):
    v = node.props.get(key)
    if v is None: return None
    if v == '' and it.scene.empty_prop_is_undefined: return None
    if v == 'none' and it.scene.none_is_undefined: return None
    try: return int(v)
    except ValueError: pass
    try: return float(v)
    except ValueError: pass
    if v.lower() == 'true': return True
    if v.lower() == 'false': return False
    return v


def _setuserprop(it, node, key, value):
    if not isinstance(node, Node): raise MaxError('setUserProp needs a node')
    node.props[key] = value if isinstance(value, str) else tostr(value)
    return True


def _box(it, name=None, width=25.0, length=25.0, height=25.0, **kw):
    for n, v in (('width', width), ('length', length), ('height', height)):
        if num_check(v, n) <= 0: raise MaxError(f'box {n} must be above 0')
    return Node(it.scene, it.get('box'), name or 'Box', width=float(width), length=float(length), height=float(height))


def _point(it, name=None, size=1.0, pos=None, **kw):
    n = Node(it.scene, it.get('point'), name or 'Point')
    if pos is not None: n.tm.rows[3] = P(*pos.v)
    return n


def _format(it, fmt, *args):
    out, a = [], list(args)
    for part in re.split(r'(%)', fmt): out.append(tostr(a.pop(0)) if part == '%' and a else part)
    it.scene.listener.append(''.join(out))


def _matchpattern(it, s, pattern=None, ignorecase=True):
    if not isinstance(s, str): raise MaxError('matchPattern needs a string')
    return fnmatch.fnmatchcase(s.lower(), pattern.lower())


def _floor(it, v): return float(math.floor(num_check(v, 'floor'))) if isinstance(v, float) else int(v)


def _classof(it, v):
    if isinstance(v, Node): return v.cls
    return {bool: Cls('BooleanClass'), int: it.get('integer'), float: it.get('float'), str: it.get('string')}.get(type(v), Cls(type(v).__name__))


def _convert_to_mesh(it, node):
    it.scene.converted.append(node)
    node.cls = it.get('editablemesh')
    return node


BUILTINS = {
    'append': lambda it, a, x: (a.append(x), a)[1],
    'finditem': lambda it, a, x: next((i + 1 for i, y in enumerate(a) if eq(y, x)), 0),
    'floor': _floor, 'abs': lambda it, v: abs(num_check(v, 'abs')),
    'getuserprop': _getuserprop, 'setuserprop': _setuserprop, 'classof': _classof, 'matchpattern': _matchpattern,
    'messagebox': lambda it, text, title=None: it.scene.messages.append((text, title)),
    'format': _format, 'timestamp': lambda it: 0,
    'standardmaterial': lambda it, name=None, diffuse=None, **kw: Mat(name, diffuse),
    'color': lambda it, r, g, b: Color(r, g, b),
    'matrix3': lambda it, a, b, c, d: M3(a, b, c, d),
    'converttomesh': _convert_to_mesh, 'box': _box, 'point': _point,
    'select': lambda it, v: None, 'clearselection': lambda it: None, 'redrawviews': lambda it: None, 'destroydialog': lambda it, v: None,
    'getcurrentexception': lambda it: '',
}
