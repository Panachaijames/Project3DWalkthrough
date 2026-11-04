// A page's mount / unmount helper for the leak checks (tests/e2e/leak.spec.ts): the offline entry installs it with
// ?test=1, the core harness's leak page always. Owner: builder A. Not part of the viewer's public API.
import type { Viewer, ViewerOptions, ViewerProject } from '../contracts';
import { createViewer } from '../viewer';

export interface MountApi {
  /** createViewer(container, project, options + extra) into the page's container; null when it worked, else the error's message. */
  mount(extra?: Partial<ViewerOptions>): string | null;
  /** dispose() the mounted viewer, if any. */
  unmount(): void;
  readonly viewer: Viewer | null;
}

declare global {
  interface Window { __wtvMount?: MountApi }
}

export function makeMountApi(container: HTMLElement, project: ViewerProject, options: ViewerOptions): MountApi {
  let viewer: Viewer | null = null;
  return {
    mount(extra) {
      if (viewer) return 'already mounted';
      try {
        viewer = createViewer(container, project, { ...options, ...(extra ?? {}) });
        return null;
      } catch (err) {
        return err instanceof Error ? err.message : String(err);
      }
    },
    unmount() {
      viewer?.dispose();
      viewer = null;
    },
    get viewer() { return viewer; },
  };
}
