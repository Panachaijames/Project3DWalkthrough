// The offline page's script (DESIGN.md 16). Owner: builder A.
// Parses the payload in <script type="application/json" id="wtv-data"> (the store's files as they are: meta.json,
// version.json, model.json, stages.json, the plan pictures as data: URLs, overrides.json), sets the title to
// presentation.documentTitle and starts the viewer in #wtv-app with the page's own address options, the furniture heights
// kept in this browser (on top of the saved ones in the file) and the test hook with ?test=1. Everything it needs is in the
// file: no network. A payload that is missing or does not parse shows a plain message instead.
// This file (and all it imports) must never contain the template's two marker texts literally: the template build checks
// each occurs exactly once.
import { parseAddressOptions } from '../address';
import type { OfflinePayload, ViewerOptions, ViewerProject } from '../contracts';
import { parsePresentation } from '../model/presentation';
import { makeMountApi } from './mount';

const isObj = (v: unknown): v is Record<string, unknown> => v !== null && typeof v === 'object' && !Array.isArray(v);

/** The payload's text -> its parts, or a plain Error saying what is wrong. */
export function readPayload(text: string | null | undefined): OfflinePayload {
  let data: unknown;
  try { data = JSON.parse(text ?? ''); } catch {
    throw new Error('The model data in this file could not be read: the file may be incomplete (an interrupted download?), download it again.');
  }
  if (!isObj(data) || data.format !== 'walkthrough-offline/1') throw new Error('This file carries no walkthrough model data (walkthrough-offline/1).');
  if (!isObj(data.project) || !isObj(data.version) || !isObj(data.model)) throw new Error('The model data in this file is incomplete (project, version, model).');
  if (!isObj(data.version.presentation) || typeof data.version.stamp !== 'string') throw new Error('The version data in this file is incomplete (presentation, stamp).');
  if (data.pictures !== undefined && !isObj(data.pictures)) throw new Error('The plan pictures in this file could not be read.');
  return data as unknown as OfflinePayload;
}

/**
 * The ViewerProject of a payload (DESIGN.md 16 "Entry"). The deleted boxes (overrides.json pieceEdits; docs/boxes/DESIGN.md
 * 4) are passed only when the file carries them: a file without them makes the project it always made, key for key.
 */
export function projectOf(p: OfflinePayload): ViewerProject {
  const pieceEdits = p.overrides?.pieceEdits;
  return {
    model: p.model,
    presentation: p.version.presentation,
    stages: p.stages ?? null,
    pictures: p.pictures ?? {},
    heights: p.overrides?.heights ?? null,
    stamp: p.version.stamp,
    ids: { projectId: p.project.id, version: p.version.version },
    ...(pieceEdits !== undefined && pieceEdits !== null ? { pieceEdits } : {}),
  };
}

function showError(app: HTMLElement, message: string): void {
  const box = document.createElement('div');
  box.setAttribute('data-wt', 'offline-error');
  box.setAttribute('role', 'alert');
  Object.assign(box.style, {
    font: '14px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif', color: '#1d2329', margin: '24px', maxWidth: '640px',
    whiteSpace: 'pre-wrap',
  });
  box.textContent = `The walkthrough could not start. ${message}`;
  app.append(box);
}

declare global {
  interface Window { __wtvStarted?: boolean }
}

function start(): void {
  // the template's DOMContentLoaded check: the script ran, so the file is not cut short inside it (fix step)
  window.__wtvStarted = true;
  const app = document.getElementById('wtv-app');
  if (!app) return;
  try {
    const payload = readPayload(document.getElementById('wtv-data')?.textContent);
    const project = projectOf(payload);
    document.title = parsePresentation(project.presentation).documentTitle;
    const address = parseAddressOptions(location.search);
    const options: ViewerOptions = { address, furnitureHeights: 'local', testHook: address.test === true };
    const mounts = makeMountApi(app, project, options);
    if (address.test === true) window.__wtvMount = mounts;
    const failed = mounts.mount();
    if (failed !== null) showError(app, failed);
  } catch (err) {
    showError(app, err instanceof Error ? err.message : String(err));
  }
}

start();
