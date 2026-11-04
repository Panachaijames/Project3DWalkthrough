// The module's viewer counters (DESIGN.md 11.7 __walkthrough.live() / created(), the leak checks). Owner: builder A.
// `live` counts the viewers of this page that were created and not yet disposed; `created` every successful createViewer.
// A createViewer that throws changes neither (11.2: "the live counter as before").
let live = 0;
let created = 0;

export const counters = {
  get live() { return live; },
  get created() { return created; },
  /** A viewer was created (the end of createViewer). */
  up(): void { live++; created++; },
  /** A viewer was disposed (once per viewer). */
  down(): void { live = Math.max(0, live - 1); },
};
