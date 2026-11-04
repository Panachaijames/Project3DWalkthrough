// parseAddressOptions: the prototypes' ?query options, exactly (DESIGN.md 11.3). Owner: builder A.
// Sources: viewer_modes.js applyUrl (mode, floor, x / y / z, yaw, pitch, lens, eye, frame, size, straight, nodownload,
// touch, cam, shot), build_replay.js start-up (build, speed, captions; any `mode` key skips the build screen, tested
// first, so it wins over build=play), the hotel page (picture=1 / 0), the offline page (test=1). Only well-formed values
// are kept; applyAddress (modes), replay.start, the visibility and the offline entry apply them. createViewer never reads
// `location` itself: the host passes its page's address.
import type { AddressOptions, ParseAddressOptions, PhotoFrame } from './contracts';

const FRAMES: readonly PhotoFrame[] = ['screen', '16:9', '3:2', '4:3', '1:1', '4:5', '9:16'];
const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v));

export const parseAddressOptions: ParseAddressOptions = search => {
  const q = typeof search === 'string' ? new URLSearchParams(search) : search;
  const out: AddressOptions = {};
  /** parseFloat of a key, or null when the key is missing or its value unreadable ('90deg' is 90, as parseFloat reads it). */
  const num = (key: string): number | null => {
    const raw = q.get(key);
    if (raw === null) return null;
    const v = parseFloat(raw);
    return Number.isFinite(v) ? v : null;
  };

  // the build replay's start-up: build=0 or any mode key -> skip; build=play -> play (build_replay.js)
  if (q.get('build') === '0' || q.has('mode')) out.build = 'skip';
  else if (q.get('build') === 'play') out.build = 'play';
  const speed = q.get('speed');
  if (speed === 'quick' || speed === 'normal' || speed === 'slow') out.speed = speed;
  if (q.get('captions') === '0') out.captions = false;

  // where to start (viewer_modes.js applyUrl)
  const mode = q.get('mode');
  if (mode === 'walk' || mode === 'ghost') out.mode = mode;
  const floor = q.get('floor');
  if (floor) out.floor = floor;
  if (q.has('x')) out.point = { x: num('x'), y: num('y'), z: num('z') };
  const yaw = num('yaw'), pitch = num('pitch'), lens = num('lens'), eye = num('eye');
  if (yaw !== null) out.yaw = yaw;
  if (pitch !== null) out.pitch = pitch;
  if (lens !== null) out.lens = clamp(lens, 12, 85);
  if (eye !== null) out.eye = clamp(eye, 0.8, 2.2);

  // the Camera tool and the flags
  if (q.get('cam') === '1') out.cam = true;
  const frame = q.get('frame');
  if (frame !== null && (FRAMES as readonly string[]).includes(frame)) out.frame = frame as PhotoFrame;
  if (q.get('size') === '4k') out.size = 3840;
  if (q.get('straight') === '1') out.straight = true;
  if (q.get('touch') === '1') out.touch = true;
  if (q.get('nodownload') === '1') out.nodownload = true;
  if (q.get('shot') === '1') out.shot = true;
  const picture = q.get('picture');
  if (picture === '1') out.picture = true;
  else if (picture === '0') out.picture = false;
  if (q.get('test') === '1') out.test = true;
  return out;
};
