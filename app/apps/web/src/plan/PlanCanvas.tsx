// The plan canvas component (docs/upload/DESIGN.md U-12.1). Owner U7. A wrapper the size of its parent, one <canvas>
// (device-pixel-ratio aware, focusable for the keys), and a tooltip <div> filled with textContent only (layer names and
// keys are drawing text). The controller (controller.ts) does the work; this file only mounts it and hands it the props.
// Where no 2D canvas exists (happy-dom in the unit tests, a browser that refuses one), a text placeholder names the plan.
import { useLayoutEffect, useRef, useState, type CSSProperties, type JSX } from 'react';
import { PlanController } from './controller';
import type { Ctx } from './draw';
import type { PlanCanvasProps } from './index';

/** Whether this environment gives a 2D canvas context. */
export function canDraw2d(): boolean {
  if (typeof document === 'undefined') return false;
  try {
    return !!document.createElement('canvas').getContext('2d') && typeof Path2D !== 'undefined';
  } catch {
    return false;
  }
}

const WRAP: CSSProperties = { position: 'relative', width: '100%', height: '100%', minHeight: 200, overflow: 'hidden' };
const CANVAS: CSSProperties = { position: 'absolute', inset: 0, width: '100%', height: '100%', display: 'block', touchAction: 'none' };
const TIP: CSSProperties = {
  position: 'absolute', zIndex: 1, pointerEvents: 'none', whiteSpace: 'pre', maxWidth: 260, overflow: 'hidden', textOverflow: 'ellipsis',
  font: '12px system-ui, sans-serif', lineHeight: '16px', color: '#24292f', background: 'rgba(255,255,255,0.96)',
  border: '1px solid #d0d7de', borderRadius: 4, padding: '3px 6px', boxShadow: '0 1px 3px rgba(0,0,0,0.12)',
};
const PLACEHOLDER: CSSProperties = { width: '100%', height: '100%', minHeight: 200, display: 'grid', placeItems: 'center' };

export function PlanCanvasView(props: PlanCanvasProps): JSX.Element {
  const [drawable] = useState(canDraw2d);
  const wrap = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const tip = useRef<HTMLDivElement>(null);
  const ctl = useRef<PlanController | null>(null);
  const latest = useRef(props);
  latest.current = props;

  useLayoutEffect(() => {
    if (!drawable) return;
    const c = canvas.current!, w = wrap.current!;
    const ctx = c.getContext('2d') as Ctx | null;
    const controller = new PlanController(c, tip.current, latest.current, ctx);
    ctl.current = controller;
    const measure = () => {
      const r = w.getBoundingClientRect();
      controller.resize(r.width, r.height, window.devicePixelRatio || 1);
    };
    const ro = typeof ResizeObserver === 'function' ? new ResizeObserver(measure) : null;
    ro?.observe(w);
    window.addEventListener('resize', measure);
    measure();
    return () => {
      ro?.disconnect();
      window.removeEventListener('resize', measure);
      controller.dispose();
      ctl.current = null;
    };
  }, [drawable]);

  useLayoutEffect(() => {
    ctl.current?.setProps(props);
  });

  const [x0, y0, x1, y1] = props.plan.extents;
  const label = `Plan of ${props.plan.count} items, ${(x1 - x0).toFixed(1)} x ${(y1 - y0).toFixed(1)} m`;
  if (!drawable) {
    return <div data-plan-canvas="placeholder" style={PLACEHOLDER}>{`${label} (this browser cannot draw the plan)`}</div>;
  }
  return (
    <div ref={wrap} data-plan-canvas="canvas" style={WRAP}>
      <canvas ref={canvas} tabIndex={0} role="img" aria-label={label} style={CANVAS} />
      <div ref={tip} data-plan-tip="" hidden style={TIP} />
    </div>
  );
}
