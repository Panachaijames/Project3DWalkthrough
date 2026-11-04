// The rise shader patch (port of build_replay.js "the walls grow: a small shader patch"; DESIGN.md 12, 13, 19).
// Owner: builder D.
//
// Each rising solid has an aDelay attribute (0..1, written by core/build per part: the sweep); uRise 0 -> 1 raises the
// floor's solids in a sweep. A solid that has not started yet is not drawn at all (so it cannot flicker against the
// outlines below it). The wall-height setting scales the mesh itself (core/heights), so hover, double-click and walking
// see it too. three.js moved from r160 (the prototypes) to r186: the patch asserts each chunk it hooks into and throws a
// clear error instead of compiling a shader that silently does nothing.
import { REVISION, type Material } from 'three';

/** One per floor: every rising solid of a floor shares its floor's values (as on the pages, which set them all alike). */
export interface RiseUniforms {
  uRise: { value: number };
  /** The floor's model level: the solids grow from it (object space, before the mesh and group transforms). */
  uBase: { value: number };
}

/** What onBeforeCompile receives (three's WebGLProgramParametersWithUniforms, the parts the patch touches). */
export interface ShaderSource {
  uniforms: Record<string, { value: unknown }>;
  vertexShader: string;
  fragmentShader: string;
}

/** The chunks the patch hooks into, per stage. */
export const RISE_MARKERS = {
  vertex: ['#include <common>', '#include <begin_vertex>'],
  fragment: ['#include <common>', '#include <clipping_planes_fragment>'],
} as const;

// The GLSL of build_replay.js, word for word (rise brK = smoothstep((uRise - aDelay * 0.6) / 0.4), min 0.004,
// discard under 0.0005: DESIGN.md 13).
const VERTEX_COMMON = '\nattribute float aDelay;\nuniform float uRise;\nuniform float uBase;\nvarying float vBrK;';
const VERTEX_BEGIN = '\n' +
  '  float brK = clamp((uRise - aDelay * 0.6) / 0.4, 0.0, 1.0);\n' +
  '  brK = brK * brK * (3.0 - 2.0 * brK);\n' +
  '  vBrK = brK;\n' +
  '  transformed.y = uBase + (transformed.y - uBase) * max(brK, 0.004);';
const FRAGMENT_COMMON = '\nvarying float vBrK;';
const FRAGMENT_CLIPPING = '\n  if (vBrK <= 0.0005) discard;';

/** Inserts `extra` after the first `marker` of `src`; throws a clear error when the marker is missing. */
function after(src: string, marker: string, extra: string, stage: 'vertex' | 'fragment'): string {
  const at = src.indexOf(marker);
  if (at < 0) {
    throw new Error(`[viewer] replay: the ${stage} shader has no "${marker}" to patch (three.js r${REVISION}); the walls cannot rise`);
  }
  return src.slice(0, at + marker.length) + extra + src.slice(at + marker.length);
}

/** The patch itself (pure: onBeforeCompile calls it). Throws before changing anything when a marker is missing. */
export function patchRiseShader(shader: ShaderSource, u: RiseUniforms): void {
  let vertex = after(shader.vertexShader, RISE_MARKERS.vertex[0], VERTEX_COMMON, 'vertex');
  vertex = after(vertex, RISE_MARKERS.vertex[1], VERTEX_BEGIN, 'vertex');
  let fragment = after(shader.fragmentShader, RISE_MARKERS.fragment[0], FRAGMENT_COMMON, 'fragment');
  fragment = after(fragment, RISE_MARKERS.fragment[1], FRAGMENT_CLIPPING, 'fragment');
  Object.assign(shader.uniforms, u);
  shader.vertexShader = vertex;
  shader.fragmentShader = fragment;
}

/** Hooks the patch into a material (recompiled on next use). The same source text for every material: one program. */
export function installRiseShader(material: Material, u: RiseUniforms): void {
  material.onBeforeCompile = shader => patchRiseShader(shader as unknown as ShaderSource, u);
  material.needsUpdate = true;
}
