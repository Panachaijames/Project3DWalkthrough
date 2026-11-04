// Builder A: packages/viewer/scripts/make-offline.mjs (DESIGN.md 16) on a store written by hand from the fixtures into
// <WT_TMP>/data (D-9.1 layout): each marker exactly once in the template (else an error), the stamp first, then a split on
// the data marker; the payload is the store's files as they are, "<" escaped as \u003c, the plan pictures as data: URLs in
// floor order; names with </script>, <!--, $' $& $` $$ and the marker texts stay inside the JSON and parse back equal.
import { spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { beforeAll, describe, expect, it } from 'vitest';
import { APP, HAND_TEMPLATE, HOSTILE, TMP, writeStore, type StoreVersion } from './store';

interface MakeOffline {
  STAMP_MARKER: string; DATA_MARKER: string;
  occurrences(text: string, marker: string): number;
  assemble(template: string, stamp: string, payload: string): string;
  payloadText(p: { meta: string; version: string; model: string; stages?: string | null; pictures?: [string, string, string][]; overrides?: string | null }): string;
  makeOffline(o: { data: string; template: string; out: string; project?: string | null; version?: number | null }): { file: string; bytes: number; stamp: string }[];
  storeVersions(data: string): { projectId: string; version: number }[];
  OfflineError: new (m: string) => Error;
}
const SCRIPT = path.join(APP, 'packages/viewer/scripts/make-offline.mjs');
const OUT = path.join(TMP, 'unit-offline');
const TEMPLATE = path.join(TMP, 'unit-template.html');
let M: MakeOffline;
let store: { root: string; versions: StoreVersion[] };

/** The text inside <script type="application/json" id="wtv-data"> ... </script> (the first </script> after it). */
function dataOf(html: string): string {
  const open = '<script type="application/json" id="wtv-data">';
  const at = html.indexOf(open);
  expect(at).toBeGreaterThan(0);
  const end = html.indexOf('</script>', at + open.length);
  return html.slice(at + open.length, end);
}
const readJson = (file: string) => JSON.parse(readFileSync(file, 'utf8'));

beforeAll(async () => {
  M = await import(pathToFileURL(SCRIPT).href) as MakeOffline;
  store = writeStore(path.join(TMP, 'data'));
  mkdirSync(TMP, { recursive: true });
  writeFileSync(TEMPLATE, HAND_TEMPLATE, 'utf8');
  rmSync(OUT, { recursive: true, force: true });
});

describe('assemble: substitute in the template only', () => {
  it('puts the stamp in, then the payload between the two pieces', () => {
    const html = M.assemble(HAND_TEMPLATE, 'c3a9408304a2', '{"a":1}');
    expect(html).toContain('<meta name="model-data" content="c3a9408304a2">');
    expect(dataOf(html)).toBe('{"a":1}');
    expect(html.endsWith('<p>the tail</p></body></html>\n')).toBe(true);
  });
  it("never expands replacement patterns: $' $& $` $$ in the payload stay as they are", () => {
    for (const evil of ["$'", '$&', '$`', '$$', "$'$&$`$$"]) {
      const html = M.assemble(HAND_TEMPLATE, '000000000000', `{"x":"${evil}"}`);
      expect(JSON.parse(dataOf(html))).toEqual({ x: evil });
      expect(M.occurrences(html, '</body>')).toBe(1);
    }
  });
  it('the marker texts inside the payload are left alone (the template is split once, before the payload goes in)', () => {
    const html = M.assemble(HAND_TEMPLATE, 'abcdefabcdef', '{"x":"__WTV_DATA__ __WTV_STAMP__"}');
    expect(JSON.parse(dataOf(html))).toEqual({ x: '__WTV_DATA__ __WTV_STAMP__' });
    expect(html).toContain('content="abcdefabcdef"');
  });
  it('refuses a template without each marker exactly once, and a stamp that is not 12 hex', () => {
    expect(() => M.assemble(HAND_TEMPLATE.replace('__WTV_DATA__', ''), '000000000000', '{}')).toThrow(/__WTV_DATA__ exactly once \(found 0\)/);
    expect(() => M.assemble(`${HAND_TEMPLATE}__WTV_DATA__`, '000000000000', '{}')).toThrow(/__WTV_DATA__ exactly once \(found 2\)/);
    expect(() => M.assemble(`__WTV_STAMP__${HAND_TEMPLATE}`, '000000000000', '{}')).toThrow(/__WTV_STAMP__ exactly once \(found 2\)/);
    expect(() => M.assemble(HAND_TEMPLATE, 'C3A9408304A2', '{}')).toThrow(/12 hex/);
    expect(() => M.assemble(HAND_TEMPLATE, '__WTV_DATA__', '{}')).toThrow(/12 hex/);
  });
});

describe('payloadText: plain concatenation, "<" escaped', () => {
  it('glues the files as they are, without line breaks between them, and escapes every "<"', () => {
    const text = M.payloadText({ meta: '{"m":1}\n', version: '{"v":"<b>"}\n', model: '{"p":[1]}\n', pictures: [['F1', 'image/png', 'AAAA'], ['F2', 'image/jpeg', 'BB==']] });
    expect(text).toBe('{"format":"walkthrough-offline/1","project":{"m":1}\n,"version":{"v":"\\u003cb>"}\n,"model":{"p":[1]}\n,'
      + '"stages":null,"pictures":{"F1":"data:image/png;base64,AAAA","F2":"data:image/jpeg;base64,BB=="},"overrides":null}');
    expect(JSON.parse(text).version.v).toBe('<b>');
  });
  it('refuses a floor key or media type that would need escaping', () => {
    expect(() => M.payloadText({ meta: '{}', version: '{}', model: '{}', pictures: [['F"1', 'image/png', 'A']] })).toThrow(/floor key/);
    expect(() => M.payloadText({ meta: '{}', version: '{}', model: '{}', pictures: [['F1', 'image/png"', 'A']] })).toThrow(/media type/);
  });
});

describe('makeOffline on the hand-made store', () => {
  it('lists the versions of the store in project and version order', () => {
    expect(M.storeVersions(store.root)).toEqual([
      { projectId: 'bank-sampeng', version: 2 }, { projectId: 'hostile-names', version: 1 }, { projectId: 'hotel-lobby', version: 1 },
    ]);
  });
  it('writes one <projectId>-v<n>.html per version, each a file of the template with its stamp and payload', () => {
    const written = M.makeOffline({ data: store.root, template: TEMPLATE, out: OUT });
    expect(written.map(w => path.basename(w.file))).toEqual(['bank-sampeng-v2.html', 'hostile-names-v1.html', 'hotel-lobby-v1.html']);
    for (const v of store.versions) {
      const html = readFileSync(path.join(OUT, `${v.projectId}-v${v.version}.html`), 'utf8');
      expect(html).toContain(`<meta name="model-data" content="${v.stamp}">`);
      expect(html.startsWith(HAND_TEMPLATE.slice(0, HAND_TEMPLATE.indexOf('__WTV_STAMP__')))).toBe(true);
      expect(html.endsWith('</script><p>the tail</p></body></html>\n')).toBe(true);
      const data = dataOf(html);
      expect(data.includes('<')).toBe(false);                               // so no </script and no <!-- inside it
      const payload = JSON.parse(data);
      const dir = v.dir, file = (n: string) => path.join(dir, n);
      expect(payload.format).toBe('walkthrough-offline/1');
      expect(payload.project).toEqual(readJson(path.join(dir, '../../meta.json')));
      expect(payload.version).toEqual(readJson(file('version.json')));
      expect(payload.model).toEqual(readJson(file('model.json')));
      expect(payload.stages).toEqual(existsSync(file('stages.json')) ? readJson(file('stages.json')) : null);
      expect(payload.overrides).toEqual(existsSync(file('overrides.json')) ? readJson(file('overrides.json')) : null);
      // the raw texts, byte for byte, in the payload (with "<" escaped)
      for (const name of ['version.json', 'model.json']) expect(data).toContain(readFileSync(file(name), 'utf8').split('<').join('\\u003c'));
    }
  });
  it('the plan pictures: data URLs of the asset files, in model floor order', () => {
    const payload = JSON.parse(dataOf(readFileSync(path.join(OUT, 'hotel-lobby-v1.html'), 'utf8')));
    expect(Object.keys(payload.pictures)).toEqual(['F1', 'F2']);
    for (const [key, file] of [['F1', 'floor1_plan.png'], ['F2', 'floor2_plan.png']] as const) {
      const m = /^data:image\/png;base64,(.+)$/.exec(payload.pictures[key]);
      expect(Buffer.from(m![1]!, 'base64').equals(readFileSync(path.join(APP, 'fixtures/pictures', file)))).toBe(true);
    }
    expect(JSON.parse(dataOf(readFileSync(path.join(OUT, 'bank-sampeng-v2.html'), 'utf8'))).pictures).toEqual({});
  });
  it('hostile names (</script>, <!--, $\' $& $` $$, the markers, <img onerror>) stay inside the JSON and parse back equal', () => {
    const html = readFileSync(path.join(OUT, 'hostile-names-v1.html'), 'utf8');
    const payload = JSON.parse(dataOf(html));
    const model = readJson(path.join(store.versions.find(v => v.projectId === 'hostile-names')!.dir, 'model.json'));
    expect(payload.model).toEqual(model);
    expect(payload.model.rooms.map((r: { label: string }) => r.label)).toEqual(HOSTILE);
    expect(payload.version.presentation.heading).toBe(`Hostile ${HOSTILE[0]}`);
    // the whole file: the template's own </script> tags only (one per script element), none from the drawing text
    expect(M.occurrences(html, '</script>')).toBe(M.occurrences(HAND_TEMPLATE, '</script>'));
    expect(M.occurrences(html, '<!--')).toBe(0);
  });
  it('the same store gives the same bytes again', () => {
    const before = readFileSync(path.join(OUT, 'hostile-names-v1.html'));
    M.makeOffline({ data: store.root, template: TEMPLATE, out: OUT, project: 'hostile-names' });
    expect(readFileSync(path.join(OUT, 'hostile-names-v1.html')).equals(before)).toBe(true);
  });
  it('--project / --version choose; a missing store or template is an error naming the npm script', () => {
    expect(M.makeOffline({ data: store.root, template: TEMPLATE, out: path.join(TMP, 'unit-offline-one'), project: 'bank-sampeng', version: 2 }).map(w => path.basename(w.file)))
      .toEqual(['bank-sampeng-v2.html']);
    expect(() => M.makeOffline({ data: path.join(TMP, 'no-such-store'), template: TEMPLATE, out: OUT })).toThrow(/npm run seed/);
    expect(() => M.makeOffline({ data: store.root, template: path.join(TMP, 'no-such-template.html'), out: OUT })).toThrow(/npm run build:offline:template/);
  });
});

// Fix step (first code review finding 16): the store files are read as strictly as the API reads them, so Node and Python
// refuse the same files (services/api/tests/test_offline.py runs both on the same damaged stores).
describe('strict reading, as the API', () => {
  const M2 = () => M as unknown as MakeOffline & { repeatedKey(text: string): string | null };
  it('repeatedKey finds a key an object repeats (decoded, at any depth), and nothing else', () => {
    const { repeatedKey } = M2();
    expect(repeatedKey('{"a":1,"b":{"a":2},"c":[{"a":1},{"a":2}]}')).toBeNull();
    expect(repeatedKey('{"a":1,"b":2,"a":3}')).toBe('a');
    expect(repeatedKey('{"x":[1,{"k":"v","k":"w"}]}')).toBe('k');
    expect(repeatedKey('{"\\u0061":1,"a":2}')).toBe('a');                         // as Python compares them: decoded
    expect(repeatedKey('{"s":"a\\"b,\\"s\\":1","t":"{\\"s\\":"}')).toBeNull();      // quotes and braces inside strings
    expect(repeatedKey('["a","a"]')).toBeNull();
  });
  it('refuses a repeated key, bad UTF-8 and a model.json changed on disk (the API refuses each)', () => {
    const damaged = (name: string, file: string, change: (b: Buffer) => Buffer) => {
      const root = path.join(TMP, `strict-${name}`);
      rmSync(root, { recursive: true, force: true });
      const s = writeStore(root);
      const target = path.join(s.root, 'projects', 'bank-sampeng', 'versions', '2', file);
      writeFileSync(target, change(readFileSync(target)));
      return () => M.makeOffline({ data: s.root, template: TEMPLATE, out: path.join(TMP, `strict-out-${name}`), project: 'bank-sampeng', version: 2 });
    };
    expect(damaged('dup', 'version.json', b => Buffer.from(b.toString('utf8').replace('{', '{"label":"twice",')))).toThrow(/repeats the key "label"/);
    expect(damaged('utf8', 'overrides.json', () => Buffer.from([0x7b, 0x22, 0xff, 0x22, 0x3a, 0x31, 0x7d]))).toThrow(/is not UTF-8/);
    expect(damaged('sha1', 'model.json', b => Buffer.concat([b, Buffer.from(' ')]))).toThrow(/does not match the modelSha1/);
  });
});

// Each test spawns node (integration: up to 6 s under load, over vitest's 5 s default).
describe('the command line', { timeout: 60_000 }, () => {
  const run = (...args: string[]) => spawnSync(process.execPath, [SCRIPT, ...args], { cwd: APP, encoding: 'utf8' });
  it('writes the files and says so (exit 0)', () => {
    const out = path.join(TMP, 'unit-offline-cli');
    const r = run('--data', store.root, '--template', TEMPLATE, '--out', out);
    expect(r.status, r.stderr).toBe(0);
    expect(r.stdout).toMatch(/make-offline: .*bank-sampeng-v2\.html {2}\d+ KB {2}\(model data [0-9a-f]{12}\)/);
    expect(existsSync(path.join(out, 'hotel-lobby-v1.html'))).toBe(true);
  });
  it('a template with a marker twice: exit 1 with a message, nothing written', () => {
    const bad = path.join(TMP, 'unit-template-bad.html'), out = path.join(TMP, 'unit-offline-bad');
    writeFileSync(bad, `${HAND_TEMPLATE}<!-- __WTV_DATA__ -->`, 'utf8');
    rmSync(out, { recursive: true, force: true });
    const r = run('--data', store.root, '--template', bad, '--out', out);
    expect(r.status).toBe(1);
    expect(r.stderr).toMatch(/^make-offline: the template .* must contain __WTV_DATA__ exactly once \(found 2\)/);
    expect(existsSync(path.join(out, 'bank-sampeng-v2.html'))).toBe(false);
  });
  it('an unknown argument: exit 1', () => {
    const r = run('--nope');
    expect(r.status).toBe(1);
    expect(r.stderr).toMatch(/unknown argument --nope/);
  });
});
