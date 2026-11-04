// The React wrapper of the framework-free viewer (DESIGN.md 15.4, 18.40).
// One viewer per (project, options, create): the effect creates it on its own div and disposes it in the cleanup, so
// StrictMode's create -> dispose -> create on the same div leaves exactly one, and a new `project` (a version change)
// disposes the old viewer before the new one is made. The callbacks are Effect Events (React 19.2+): always the latest
// ones, without re-creating the viewer and without writing a ref during render; called only from the effect and from the
// viewer's event, never during render. createViewer cleans up after itself when it throws (DESIGN.md 11.2), so a failed
// create leaves nothing to dispose here.
//
// Unmount: React takes the page's DOM out of the document BEFORE it runs effect cleanups, so the cleanup above would dispose
// a viewer whose canvas is no longer in the document; three's OrbitControls then removes its capturing keydown listener
// from canvas.getRootNode() (the detached subtree, not the document) and the document keeps it, holding the controls and
// the camera (seen in web-leak.spec.ts; contract-issues/F.md F-5). A layout-effect cleanup runs while the DOM is still in
// place: on unmount it disposes the live viewer there, and the effect's cleanup then finds it disposed (dispose() is
// idempotent). The ref is written only inside effects.
import { createViewer, type CreateViewer, type HeightMap, type Viewer, type ViewerOptions, type ViewerProject } from '@walkthrough/viewer';
import { useEffect, useEffectEvent, useLayoutEffect, useRef } from 'react';

export interface ViewerHostProps {
  /** Memoised by the page (projectId, version, stamp): a new object re-creates the viewer. */
  project: ViewerProject;
  /** Memoised by the page (the address): a new object re-creates the viewer. */
  options?: ViewerOptions;
  /** The viewer's heightschange (typed or reset in the legend): the kinds whose height differs from the model's. */
  onHeightsChange?: (heights: HeightMap) => void;
  /** createViewer threw (the viewer has already cleaned up after itself). */
  onError?: (err: unknown) => void;
  /** A viewer was made (also after a failed attempt, e.g. StrictMode's second mount): the page clears its error. */
  onCreated?: (viewer: Viewer) => void;
  /** Tests pass a fake; the app uses the viewer package's createViewer. */
  create?: CreateViewer;
}

export function ViewerHost({ project, options, onHeightsChange, onError, onCreated, create = createViewer }: ViewerHostProps) {
  const ref = useRef<HTMLDivElement>(null);
  /** The viewer the effect made and has not disposed yet (written only in effects). */
  const live = useRef<Viewer | null>(null);
  const heightsChanged = useEffectEvent((heights: HeightMap) => onHeightsChange?.(heights));
  const failed = useEffectEvent((err: unknown) => onError?.(err));
  const created = useEffectEvent((viewer: Viewer) => onCreated?.(viewer));
  useEffect(() => {
    let viewer: Viewer;
    try {
      viewer = create(ref.current!, project, options);
    } catch (err) {
      failed(err);
      return;
    }
    live.current = viewer;
    const off = viewer.on('heightschange', e => heightsChanged(e.heights));
    created(viewer);
    return () => {
      off();
      viewer.dispose();
      if (live.current === viewer) live.current = null;
    };
  }, [project, options, create]);
  // Unmount only (no deps): dispose while the container is still in the document (see the note above).
  useLayoutEffect(() => () => {
    const viewer = live.current;
    live.current = null;
    viewer?.dispose();
  }, []);
  return <div ref={ref} className="viewer-host" data-testid="viewer-host" />;
}
