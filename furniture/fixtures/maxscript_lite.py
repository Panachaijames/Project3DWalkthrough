"""A small MAXScript toolkit for the tests of furniture_max.py (3ds Max is not installed on this machine).

1. tokenize / lint / unresolved / arity_errors: a token-level lint (brackets, quotes, if-then-else, for-do, case-of, fn, try-catch,
   local / global placement, names that nothing declares, calls with the wrong number of arguments).
2. Interp: an interpreter for the small, conservative subset of MAXScript the generated scripts use (command-style calls, if / for,
   blocks, arrays, point and matrix values, user properties, layers, a box with a transform), over a mock scene. It runs the
   generated functions, so that logic slips (a wrong index, a name that is never set, a number sent to the wrong place) show up.
   What it knows about 3ds Max is only what is written down here (see MockMax): it can show that the script does what the author
   meant under that reading of Max, not that Max agrees.
"""
import math, re
from collections import namedtuple

Tok = namedtuple('Tok', 'kind text line pos space')

TOKEN = re.compile('|'.join([
    r'(?P<comment>--[^\n]*)',
    r'(?P<str>"(?:[^"\\\n]|\\.)*")',
    r'(?P<num>\d+\.\d+(?:[eE][+-]?\d+)?|\d+(?:[eE][+-]?\d+)?)',
    r'(?P<hopen>#\()',
    r'(?P<sym>#[A-Za-z_][A-Za-z0-9_]*)',
    r'(?P<id>[A-Za-z_][A-Za-z0-9_]*)',
    r'(?P<op>==|!=|<=|>=|\+=|-=|\*=|/=|[-+*/^=<>.,:;&?$%@!~])',
    r'(?P<open>[(\[])',
    r'(?P<close>[)\]])',
    r'(?P<nl>\n)',
    r'(?P<ws>[ \t\r]+)',
]))
KEYWORDS = {'global', 'local', 'fn', 'if', 'then', 'else', 'do', 'for', 'in', 'to', 'by', 'while', 'where', 'case', 'of', 'try',
            'catch', 'return', 'and', 'or', 'not', 'as', 'on', 'collect', 'with', 'exit', 'continue', 'true', 'false', 'undefined',
            'ok', 'rollout', 'group'}
CONTROLS = {'checkbox', 'spinner', 'button', 'label', 'radiobuttons', 'dropdownlist', 'edittext', 'listbox', 'slider', 'rollout'}


def tokenize(text):
    toks, errs, pos, line, space = [], [], 0, 1, False
    while pos < len(text):
        m = TOKEN.match(text, pos)
        if not m:
            errs.append(f'line {line}: cannot read {text[pos:pos + 20]!r}'); pos += 1; continue
        kind, s = m.lastgroup, m.group()
        if kind == 'ws': space = True
        elif kind == 'comment': pass
        else:
            if kind == 'hopen': kind = 'open'
            toks.append(Tok(kind, s, line, pos, space)); space = False
            if kind == 'nl': line += 1; space = True
        pos = m.end()
    return toks, errs


def structure(toks):                       # bracket matching and the depth of every token (a close counts at the outer depth)
    errs, match, stack, depth, d = [], {}, [], [], 0
    close_of = {'(': ')', '#(': ')', '[': ']'}
    for i, t in enumerate(toks):
        if t.kind == 'close':
            d -= 1
            if stack:
                j = stack.pop()
                if close_of[toks[j].text] != t.text: errs.append(f'line {t.line}: {t.text} closes {toks[j].text} of line {toks[j].line}')
                match[i], match[j] = j, i
            else: errs.append(f'line {t.line}: {t.text} without an opening bracket')
        depth.append(d)
        if t.kind == 'open': stack.append(i); d += 1
    for j in stack: errs.append(f'line {toks[j].line}: {toks[j].text} never closed')
    return match, depth, errs


def lint(text):
    toks, errs = tokenize(text)
    match, depth, e2 = structure(toks)
    errs = errs + e2
    if e2: return errs
    n = len(toks)

    def forward(i, wanted, op=False):      # a keyword (or the = operator) after token i on its line, at its depth
        for j in range(i + 1, n):
            t = toks[j]
            if depth[j] < depth[i]: return None
            if depth[j] != depth[i]: continue
            if t.kind == 'nl': return None
            if op and t.kind == 'op' and t.text in wanted: return j
            if not op and t.kind == 'id' and t.text.lower() in wanted: return j
        return None

    def backward(i, wanted):               # same, looking back along the line
        for j in range(i - 1, -1, -1):
            t = toks[j]
            if depth[j] < depth[i]: return None
            if depth[j] != depth[i]: continue
            if t.kind == 'nl': return None
            if t.kind == 'id' and t.text.lower() in wanted: return j
        return None

    def before_else(i):                    # the nearest then / do / if / else before an else, at its depth, across lines
        j = i - 1
        while j >= 0:
            t = toks[j]
            if t.kind == 'close' and depth[j] == depth[i]: j = match[j] - 1; continue      # a whole (...) group
            if depth[j] < depth[i]: return None
            if depth[j] == depth[i] and t.kind == 'id' and t.text.lower() in ('then', 'do', 'if', 'else'): return t.text.lower()
            j -= 1
        return None

    tries = catches = 0
    for i, t in enumerate(toks):
        if t.kind != 'id': continue
        w = t.text.lower()
        if w == 'if':
            if forward(i, ('then', 'do')) is None: errs.append(f'line {t.line}: if without then / do on its line')
        elif w in ('for', 'while'):
            if forward(i, ('do', 'collect')) is None: errs.append(f'line {t.line}: {w} without do / collect on its line')
        elif w == 'case':
            j = forward(i, ('of',))
            if j is None: errs.append(f'line {t.line}: case without of'); continue
            k = j + 1
            while k < n and toks[k].kind == 'nl': k += 1
            if k >= n or toks[k].text != '(': errs.append(f'line {t.line}: case ... of needs a ( block next')
        elif w == 'on':
            if forward(i, ('do',)) is None: errs.append(f'line {t.line}: on <control> <event> without do')
        elif w == 'then':
            if backward(i, ('if',)) is None: errs.append(f'line {t.line}: then without if on its line')
        elif w == 'do':
            if backward(i, ('if', 'for', 'while', 'on', 'with')) is None: errs.append(f'line {t.line}: do without if / for / while / on on its line')
        elif w == 'else':
            if before_else(i) != 'then': errs.append(f'line {t.line}: else without a matching then')
        elif w == 'where':
            if backward(i, ('for',)) is None: errs.append(f'line {t.line}: where outside a for')
        elif w == 'try': tries += 1
        elif w == 'catch': catches += 1
        elif w == 'local':
            if depth[i] < 1: errs.append(f'line {t.line}: local outside a block')
        elif w == 'global':
            if depth[i] != 0: errs.append(f'line {t.line}: global inside a block')
        elif w == 'return':
            if depth[i] < 1: errs.append(f'line {t.line}: return outside a block')
        elif w == 'fn':
            if depth[i] != 0: errs.append(f'line {t.line}: fn inside a block')
            if forward(i, ('=',), op=True) is None: errs.append(f'line {t.line}: fn without =')
    if tries != catches: errs.append(f'try {tries} / catch {catches}')
    return errs


def declared(toks):
    """Names the text declares (global, fn and its parameters, local, for variables, rollout controls) and its functions."""
    names, fns = set(), {}
    for i, t in enumerate(toks):
        if t.kind != 'id': continue
        w, nxt = t.text.lower(), (toks[i + 1] if i + 1 < len(toks) else None)
        if w in ('global', 'local', 'for') and nxt and nxt.kind == 'id': names.add(nxt.text)
        elif w in CONTROLS and nxt and nxt.kind == 'id': names.add(nxt.text)
        elif w == 'fn' and nxt and nxt.kind == 'id':
            j, params = i + 2, []
            while j < len(toks) and not (toks[j].kind == 'op' and toks[j].text == '='):
                if toks[j].kind == 'id': params.append(toks[j].text)
                j += 1
            names.add(nxt.text); names.update(params); fns[nxt.text.lower()] = (nxt.text, params)
    return names, fns


def words(toks):
    """(variables used, property names after a dot, keyword-argument names before a colon)."""
    used, props, kwargs = set(), set(), set()
    for i, t in enumerate(toks):
        if t.kind != 'id' or t.text.lower() in KEYWORDS: continue
        prev = toks[i - 1] if i else None
        nxt = toks[i + 1] if i + 1 < len(toks) else None
        if prev and prev.kind == 'op' and prev.text == '.': props.add(t.text)
        elif nxt and nxt.kind == 'op' and nxt.text == ':' and not nxt.space: kwargs.add(t.text)
        else: used.add(t.text)
    return used, props, kwargs


def unresolved(text, builtins=()):
    """Names that are used but declared nowhere they can be seen: a function sees its own parameters and locals, the rollout its
    controls and locals, everything sees the globals and the functions. Words that are not names (builtins) are the caller's list."""
    toks, _ = tokenize(text)
    match, depth, errs = structure(toks)
    if errs: return {'<brackets>'}
    n, units, i, glob = len(toks), [], 0, set()
    while i < n:                                                    # the top-level units: fn, rollout, everything else
        t = toks[i]
        if depth[i] == 0 and t.kind == 'id' and t.text.lower() in ('fn', 'rollout'):
            j = i + 1
            while j < n and not (toks[j].kind == 'open' and depth[j] == 0): j += 1
            units.append(toks[i:match[j] + 1]); i = match[j] + 1
            glob.add(units[-1][1].text)                             # the function's (or rollout's) own name
        else:
            if depth[i] == 0 and t.kind == 'id' and t.text.lower() == 'global' and toks[i + 1].kind == 'id': glob.add(toks[i + 1].text)
            units.append(toks[i:i + 1]); i += 1
    known_global = {g.lower() for g in glob} | {b.lower() for b in builtins}
    out = set()
    for u in units:
        names, _ = declared(u)
        used, _, _ = words(u)
        known = known_global | {x.lower() for x in names}
        out |= {w for w in used if w.lower() not in known}
    return out


def arity_errors(text):
    """Statement lines that start with one of the text's own functions: the number of arguments must be its number of parameters."""
    toks, _ = tokenize(text)
    match, depth, e = structure(toks)
    if e: return e
    _, fns = declared(toks)
    errs, i, n = [], 0, len(toks)
    while i < n:
        t = toks[i]
        if t.kind == 'id' and t.text.lower() in fns and (i == 0 or toks[i - 1].kind == 'nl') and fns[t.text.lower()][1]:
            atoms, j, pure = 0, i + 1, True
            while j < n and not (toks[j].kind == 'nl' and depth[j] == depth[i]):
                u = toks[j]
                if u.kind == 'open': atoms += 1; j = match[j]
                elif u.kind == 'op' and u.text == '.': pass                    # a.b: one atom (the b is not counted below)
                elif u.kind == 'op': pure = False; break
                elif u.kind == 'id' and toks[j - 1].kind == 'op' and toks[j - 1].text == '.': pass
                else: atoms += 1
                j += 1
            if pure and atoms != len(fns[t.text.lower()][1]):
                errs.append(f'line {t.line}: {t.text} takes {len(fns[t.text.lower()][1])} arguments, the call has {atoms}')
        i += 1
    return errs
