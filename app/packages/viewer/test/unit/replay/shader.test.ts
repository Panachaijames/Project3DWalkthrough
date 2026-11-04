// Builder D: the rise shader patch (DESIGN.md 12, 13, 19): it hooks into the chunks three r186 still has, injects the
// prototype's GLSL word for word, hands the floor's uniforms to the program, and throws a clear error, changing nothing,
// when a chunk is missing (a later three.js could rename one).
import { MeshBasicMaterial, MeshLambertMaterial, MeshStandardMaterial, REVISION, ShaderLib } from 'three';
import { describe, expect, it } from 'vitest';
import { installRiseShader, patchRiseShader, RISE_MARKERS, type RiseUniforms, type ShaderSource } from '../../../src/replay/shader';

const source = (lib: { vertexShader: string; fragmentShader: string }): ShaderSource =>
  ({ uniforms: {}, vertexShader: lib.vertexShader, fragmentShader: lib.fragmentShader });
const uniforms = (): RiseUniforms => ({ uRise: { value: 0.25 }, uBase: { value: 3.7 } });

describe('patchRiseShader', () => {
  it('finds its four chunks in three r186 (standard, basic and lambert materials)', () => {
    expect(REVISION).toBe('186');
    for (const lib of [ShaderLib.physical, ShaderLib.basic, ShaderLib.lambert]) {
      for (const m of RISE_MARKERS.vertex) expect(lib.vertexShader).toContain(m);
      for (const m of RISE_MARKERS.fragment) expect(lib.fragmentShader).toContain(m);
    }
  });

  it('injects the prototype GLSL after each chunk and hands over the uniforms', () => {
    const sh = source(ShaderLib.physical), u = uniforms();
    const before = { ...sh };
    patchRiseShader(sh, u);
    expect(sh.uniforms.uRise).toBe(u.uRise);
    expect(sh.uniforms.uBase).toBe(u.uBase);
    expect(sh.vertexShader).toContain('#include <common>\nattribute float aDelay;\nuniform float uRise;\nuniform float uBase;\nvarying float vBrK;');
    expect(sh.vertexShader).toContain('#include <begin_vertex>\n' +
      '  float brK = clamp((uRise - aDelay * 0.6) / 0.4, 0.0, 1.0);\n' +
      '  brK = brK * brK * (3.0 - 2.0 * brK);\n' +
      '  vBrK = brK;\n' +
      '  transformed.y = uBase + (transformed.y - uBase) * max(brK, 0.004);');
    expect(sh.fragmentShader).toContain('#include <common>\nvarying float vBrK;');
    expect(sh.fragmentShader).toContain('#include <clipping_planes_fragment>\n  if (vBrK <= 0.0005) discard;');
    // only once each, and nothing else changed
    expect(sh.vertexShader.split('attribute float aDelay;').length).toBe(2);
    expect(sh.fragmentShader.split('discard;').length).toBe(before.fragmentShader.split('discard;').length + 1);
    expect(sh.vertexShader.length).toBeGreaterThan(before.vertexShader.length);
  });

  it.each([
    ['vertex', '#include <common>'], ['vertex', '#include <begin_vertex>'],
    ['fragment', '#include <common>'], ['fragment', '#include <clipping_planes_fragment>'],
  ] as const)('throws a clear error when the %s shader has no %s, and changes nothing', (stage, marker) => {
    const sh = source(ShaderLib.physical);
    if (stage === 'vertex') sh.vertexShader = sh.vertexShader.split(marker).join('/* gone */');
    else sh.fragmentShader = sh.fragmentShader.split(marker).join('/* gone */');
    const copy = { ...sh, uniforms: {} };
    expect(() => patchRiseShader(sh, uniforms())).toThrow(`[viewer] replay: the ${stage} shader has no "${marker}" to patch (three.js r186)`);
    expect(sh).toEqual(copy);
  });

  it('installs on a material: onBeforeCompile, a recompile, one program cache key for every patched material', () => {
    const a = new MeshStandardMaterial(), b = new MeshStandardMaterial(), c = new MeshBasicMaterial(), d = new MeshLambertMaterial();
    const plain = a.customProgramCacheKey();
    const v = [a, b, c, d].map(m => m.version);
    for (const m of [a, b, c, d]) installRiseShader(m, uniforms());
    [a, b, c, d].forEach((m, i) => expect(m.version).toBe(v[i]! + 1));
    expect(a.customProgramCacheKey()).not.toBe(plain);
    expect(b.customProgramCacheKey()).toBe(a.customProgramCacheKey());
    const sh = source(ShaderLib.physical), u = uniforms();
    installRiseShader(a, u);
    a.onBeforeCompile(sh as never, null as never);
    expect(sh.uniforms.uRise).toBe(u.uRise);
    expect(sh.vertexShader).toContain('transformed.y = uBase');
  });
});
