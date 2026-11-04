// Scaffold (complete; everyone uses it, nobody else edits it). DESIGN.md 11.6: elements with text only.
//
// el() has no HTML input at all: text goes in with textContent, children are nodes or strings (text nodes), and styles
// are set through element.style (CSSOM; custom properties with setProperty), never a `style` attribute string, so the
// viewer works under a strict style-src. Drawing text (room, layer, family, floor names, captions) is safe in `text`,
// `title`, attribute values and string children. Attribute NAMES come from our code: `style` and event-handler (`on*`)
// attributes are refused.
import type { El } from '../contracts';

export const el: El = (tag, props, children) => {
  const node = document.createElement(tag);
  if (props) {
    if (props.cls !== undefined) node.className = props.cls;
    if (props.wt !== undefined) node.setAttribute('data-wt', props.wt);
    if (props.attrs) {
      for (const [name, value] of Object.entries(props.attrs)) {
        const lower = name.toLowerCase();
        if (lower === 'style' || lower.startsWith('on')) throw new Error(`[viewer] el(): attribute '${name}' is not allowed`);
        node.setAttribute(name, value);
      }
    }
    if (props.text !== undefined) node.textContent = props.text;
    if (props.title !== undefined) node.title = props.title;
    if (props.style) {
      for (const [key, value] of Object.entries(props.style)) {
        if (value === undefined || value === null) continue;
        if (key.startsWith('--')) node.style.setProperty(key, String(value));
        else (node.style as unknown as Record<string, unknown>)[key] = value;
      }
    }
  }
  if (children) {
    for (const child of children) {
      if (child === null || child === undefined) continue;
      node.append(typeof child === 'string' ? document.createTextNode(child) : child);
    }
  }
  return node;
};

/** Removes every child of the node. */
export function clear(node: Node): void {
  while (node.firstChild) node.removeChild(node.firstChild);
}
