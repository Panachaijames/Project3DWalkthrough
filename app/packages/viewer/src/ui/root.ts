// createRoot: <div class="wtv" data-wt="root" data-model-stamp="..."> inside the container (DESIGN.md 11.6, 11.8, 18.17).
// Owner: builder C.
//   * 100 % of the container, position relative, overflow hidden, `container: wtv / size` (BASE_CSS); every overlay is an
//     absolute child of it; --accent on the root (the other custom properties in BASE_CSS).
//   * The viewer's CSS is ONE constructed CSSStyleSheet in document.adoptedStyleSheets (the shadow root's when the container
//     lives in one), taken out on dispose; where constructed sheets are missing, one <style> inside the root (removed with
//     it). A strict style-src blocks a runtime <style> but not a constructed sheet or CSSOM styles, so the viewer needs no
//     'unsafe-inline'. Each module adds its chunk once through addStyle (the root keeps the text and calls replaceSync).
//   * The hint line ([data-wt=hint]) and the error box ([data-wt=error], hidden until ctx.reportError fills it).
//   * Root flags for CSS: setFlag('fp' | 'camopen' | 'crowded' | 'touchui' | 'replay') -> data-<flag> (the prototypes' body
//     classes vm-fp, vm-camopen, vm-crowded, vm-touchui, br-on).
import type { CreateRoot, RootApi } from '../contracts';
import { BASE_CSS } from './css';
import { el } from './dom';

type SheetHost = { adoptedStyleSheets: CSSStyleSheet[] };

/** Where the viewer's constructed sheet goes (the document, or the shadow root holding the container), or null when constructed sheets are missing. */
function sheetHost(container: HTMLElement): SheetHost | null {
  try {
    if (typeof CSSStyleSheet !== 'function' || !('replaceSync' in CSSStyleSheet.prototype)) return null;
    const node = container.getRootNode();
    const host = (typeof ShadowRoot === 'function' && node instanceof ShadowRoot ? node : container.ownerDocument) as unknown as Partial<SheetHost>;
    if (!Array.isArray(host.adoptedStyleSheets)) return null;
    new CSSStyleSheet();
    return host as SheetHost;
  } catch {
    return null;
  }
}

export const createRoot: CreateRoot = (container, accent, stamp, disposer) => {
  const root = el('div', { cls: 'wtv', wt: 'root', attrs: { 'data-model-stamp': stamp }, style: { '--accent': accent } as Partial<CSSStyleDeclaration> });
  const hint = el('div', { wt: 'hint' });
  const errorBox = el('div', { wt: 'error', attrs: { role: 'alert' } });
  errorBox.hidden = true;
  root.append(hint, errorBox);

  const chunks: string[] = [];
  const host = sheetHost(container);
  let sheet: CSSStyleSheet | null = null;
  let styleEl: HTMLStyleElement | null = null;
  if (host) {
    sheet = new CSSStyleSheet();
    host.adoptedStyleSheets = [...host.adoptedStyleSheets, sheet];
  } else {
    styleEl = el('style');
    root.prepend(styleEl);
  }

  container.append(root);
  disposer.add(() => {
    if (host && sheet) host.adoptedStyleSheets = host.adoptedStyleSheets.filter(s => s !== sheet);
    root.remove();
  });

  const api: RootApi = {
    root,
    hint,
    errorBox,
    addStyle(css: string) {
      if (chunks.includes(css)) return;                              // each chunk once
      chunks.push(css);
      const text = chunks.join('\n');
      if (sheet) sheet.replaceSync(text);
      else if (styleEl) styleEl.textContent = text;
    },
    setFlag(flag, on) {
      if (on) root.setAttribute(`data-${flag}`, '');
      else root.removeAttribute(`data-${flag}`);
    },
  };
  api.addStyle(BASE_CSS);
  return api;
};
