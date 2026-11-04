// Builder A: parseAddressOptions (DESIGN.md 11.3, 17.2): the prototypes' address options exactly. Typos dropped, clamps,
// any `mode` key -> skip even with build=play, `point` whenever `x` is present with null for missing / unreadable values.
import { describe, expect, it } from 'vitest';
import { parseAddressOptions } from '../../../src/address';

const p = (q: string) => parseAddressOptions(q);

describe('parseAddressOptions', () => {
  it('an empty address gives nothing', () => {
    expect(p('')).toEqual({});
    expect(p('?')).toEqual({});
  });

  it('build: build=0 -> skip, build=play -> play, anything else absent', () => {
    expect(p('?build=0').build).toBe('skip');
    expect(p('?build=play').build).toBe('play');
    expect(p('?build=1').build).toBeUndefined();
    expect(p('?build=Play').build).toBeUndefined();
  });

  it('any mode key skips the build screen, even mode=orbit, mode= or a typo, and wins over build=play', () => {
    for (const q of ['?mode=walk', '?mode=orbit', '?mode=', '?mode=wlak', '?build=play&mode=ghost', '?mode=walk&build=play', '?mode']) {
      expect(p(q).build, q).toBe('skip');
    }
  });

  it('mode is kept only for walk and ghost; floor as written', () => {
    expect(p('?mode=walk').mode).toBe('walk');
    expect(p('?mode=ghost').mode).toBe('ghost');
    expect(p('?mode=orbit').mode).toBeUndefined();
    expect(p('?mode=Walk').mode).toBeUndefined();
    expect(p('?floor=L2').floor).toBe('L2');
    expect(p('?floor=no-such floor').floor).toBe('no-such floor');
    expect(p('?floor=').floor).toBeUndefined();
  });

  it('point is there whenever x is, each value parseFloat or null; without x, y and z are not read', () => {
    expect(p('?x=1.5&y=2&z=-3').point).toEqual({ x: 1.5, y: 2, z: -3 });
    expect(p('?x=1.5').point).toEqual({ x: 1.5, y: null, z: null });
    expect(p('?x=abc&z=4').point).toEqual({ x: null, y: null, z: 4 });
    expect(p('?x=&z=').point).toEqual({ x: null, y: null, z: null });
    expect(p('?x=12m&z=3.5deg').point).toEqual({ x: 12, y: null, z: 3.5 });   // parseFloat reads the number in front
    expect(p('?y=2&z=3').point).toBeUndefined();
  });

  it('yaw, pitch, lens, eye: parseFloat, unreadable dropped, lens clamped 12 - 85, eye 0.8 - 2.2', () => {
    expect(p('?yaw=90&pitch=-10')).toMatchObject({ yaw: 90, pitch: -10 });
    expect(p('?yaw=90deg').yaw).toBe(90);
    expect(p('?yaw=abc').yaw).toBeUndefined();
    expect(p('?lens=50').lens).toBe(50);
    expect(p('?lens=5').lens).toBe(12);
    expect(p('?lens=200').lens).toBe(85);
    expect(p('?lens=x').lens).toBeUndefined();
    expect(p('?eye=1.7').eye).toBe(1.7);
    expect(p('?eye=0.1').eye).toBe(0.8);
    expect(p('?eye=9').eye).toBe(2.2);
    expect(p('?eye=').eye).toBeUndefined();
  });

  it('frame: one of the seven; size: only 4k; speed: quick / normal / slow', () => {
    for (const f of ['screen', '16:9', '3:2', '4:3', '1:1', '4:5', '9:16']) expect(p(`?frame=${encodeURIComponent(f)}`).frame).toBe(f);
    expect(p('?frame=2:1').frame).toBeUndefined();
    expect(p('?size=4k').size).toBe(3840);
    expect(p('?size=4K').size).toBeUndefined();
    expect(p('?size=1920').size).toBeUndefined();
    expect(p('?speed=quick').speed).toBe('quick');
    expect(p('?speed=slow').speed).toBe('slow');
    expect(p('?speed=fast').speed).toBeUndefined();
  });

  it('flags only as =1; captions=0; picture=0 | 1; test=1', () => {
    expect(p('?cam=1&straight=1&touch=1&nodownload=1&shot=1&test=1')).toEqual({ cam: true, straight: true, touch: true, nodownload: true, shot: true, test: true });
    expect(p('?cam=true&straight=yes&touch=0&nodownload=&shot=2&test=0')).toEqual({});
    expect(p('?captions=0').captions).toBe(false);
    expect(p('?captions=1').captions).toBeUndefined();
    expect(p('?picture=1').picture).toBe(true);
    expect(p('?picture=0').picture).toBe(false);
    expect(p('?picture=yes').picture).toBeUndefined();
  });

  it('takes a URLSearchParams as well as a string', () => {
    expect(parseAddressOptions(new URLSearchParams('mode=walk&floor=L1&x=1&z=2&lens=35'))).toEqual({
      build: 'skip', mode: 'walk', floor: 'L1', point: { x: 1, y: null, z: 2 }, lens: 35,
    });
  });

  it('the offline specs address: ?build=0&nodownload=1&test=1', () => {
    expect(p('?build=0&nodownload=1&test=1')).toEqual({ build: 'skip', nodownload: true, test: true });
  });
});
