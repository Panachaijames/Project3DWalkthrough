// The test ids of the rooms milestone's screens (docs/rooms/DESIGN.md R-6.4, R-12.6; ACCEPTANCE RA-12). Written by the
// scaffold R0 and FROZEN: the components (R6) put them on their elements as `data-testid`, and the browser specs
// (tests/e2e/rooms.spec.ts, upload.spec.ts) read them from here, so a screen and its spec can be written apart. An id
// that is missing goes in your own docs/rooms/contract-issues file; use a local id of your own until it is added.
//
// Rules: one element per id unless the comment says "each"; an "each" element also carries what tells it apart in a data
// attribute (`data-key` = the floor key, `data-id` = a room, stair or flag id, `data-index` = an index into a fixes
// list). State is in data attributes too, never in the id. This module imports nothing, so a spec can import it.

/** Which way a draft is built: the values of `data-rules` on RULES_LINE. */
export type RulesState = 'new' | 'earlier';

export const TID = {
  // ---- the one line on the Floors, Build and Check steps (R-12.6) and its button
  /** The line that says which way the draft is built; `data-rules` = 'new' | 'earlier'. One per step. */
  rulesLine: 'rules-line',
  /** The button in the line (only with 'earlier'): "Use the new floor plates, ceilings and stairs". */
  rulesUseNew: 'rules-use-new',
  /** The pre-build checklist's warning line when the draft is built the earlier way. */
  checklistRules: 'checklist-rules',

  // ---- Floors step
  /** Each floor card's "Ceiling height" input (its placeholder is the default of R-5.1); inside `floor-card`. */
  ceilingHeight: 'ceiling-height',
  /** The fold "Earlier build rules" (a <details>, closed by default). */
  earlierRules: 'earlier-rules',
  /** The fold's first control (a select): value 'new' ("as built now") | 'earlier' ("the earlier way"). */
  rulesChoice: 'rules-choice',
  /** The fold's second control (a select, only with 'new'): value 'on' | 'off'. */
  ceilingsChoice: 'ceilings-choice',

  // ---- Build and Save steps: the counts per floor (each row carries data-key)
  /** Each floor's row of the three counts. */
  roomCounts: 'room-counts',
  /** In a row: "rooms closed" (its text is the number). */
  countRooms: 'count-rooms-closed',
  /** In a row: "names placed". */
  countNames: 'count-names-placed',
  /** In a row: "stairs you can climb". */
  countStairs: 'count-stairs-climb',

  // ---- Check step: the ticks above the plan and the counts in the page
  showRooms: 'show-rooms',
  showPlate: 'show-plate',
  showFurniture: 'show-furniture',
  /** The counts of the floor on screen (their text is the number): rooms, holes, stairs you can climb, stairs in all. */
  checkRooms: 'check-count-rooms',
  checkHoles: 'check-count-holes',
  checkStairsClimb: 'check-count-stairs-climb',
  checkStairs: 'check-count-stairs',

  // ---- Check step: the tools. The existing select `check-tool` gains the values 'draw-line' and 'rooms'.
  checkTool: 'check-tool',
  /** The hint shown while a line is being drawn (after the first click). */
  drawLineHint: 'draw-line-hint',

  // ---- Check step: the room panel (a click in a room, or where there is no room, with the tool Rooms and stairs)
  /** The panel; `data-id` = the space id, or '' for a place with no room; `data-at` = "x,y" (sheet m). */
  roomPanel: 'room-panel',
  roomName: 'room-name',
  /** Tick "No floor here". */
  roomNoFloor: 'room-no-floor',
  /** Tick "No ceiling". */
  roomNoCeiling: 'room-no-ceiling',
  /** Button "Floor here" (a place with no room). */
  roomFloorHere: 'room-floor-here',
  /** Button "It is outdoors" (a place with no room). */
  roomOutdoors: 'room-outdoors',
  roomPanelClose: 'room-panel-close',

  // ---- Check step: the stair panel (a click on a stair)
  /** The panel; `data-id` = the overlay's stair id; `data-state` = 'climb' | 'lines'. */
  stairPanel: 'stair-panel',
  /** Button "This is the bottom" (then one pick on the bottom tread); `data-picking` while the pick is awaited. */
  stairBottom: 'stair-bottom',
  /** Button "Keep as lines". */
  stairLines: 'stair-keep-lines',
  /** Button "Climb it as drawn". */
  stairClimb: 'stair-climb',
  /** Button that takes the stair's fix back ("Decide automatically"). */
  stairAuto: 'stair-auto',
  stairPanelClose: 'stair-panel-close',

  // ---- Check step: the flag cards' buttons (each inside its `flag` card, which carries data-id)
  /** "Close it here" on a slab-gap flag with a mouth. */
  flagCloseHere: 'flag-close-here',
  /** "It is outdoors" on a slab-gap flag. */
  flagOutdoors: 'flag-outdoors',
  /** "Not a doorway: one room" on a doorway flag. */
  flagNotDoorway: 'flag-not-doorway',
  /** The hint under an old-rule plate-dropped flag, with its button "Use the new floor plates, ceilings and stairs". */
  flagEarlierHint: 'flag-earlier-hint',

  // ---- Check step: the list "Fixes on this floor" (beside the set-aside list)
  fixesList: 'fixes-list',
  /** Each row; `data-kind` = 'closing' | 'closing-removed' | 'room' | 'stair'; `data-index` = its index in the fixes
   *  list of its kind; `data-waiting` when it waits for Rebuild. */
  fixRow: 'fix-row',
  /** Each row's Remove button. */
  fixRemove: 'fix-remove',
  /** Each "waiting for Rebuild" mark (in the list, the panels and the flag cards). */
  fixWaiting: 'fix-waiting',

  // ---- Check step: the set-aside list, the Heights panel, the list of changes
  /** Each set-aside row's tick "The floor runs past it" (inside `set-aside-row`). */
  setAsideFloorPast: 'set-aside-floor-past',
  /** Each floor's ceiling height in the Heights panel (inside `heights-panel`; data-key). */
  heightsCeiling: 'heights-ceiling',
  /** The first row of the list of changes when a Rebuild made a floor's plate smaller by 2 m2 or more (data-key). */
  lostFloor: 'diff-lost-floor',
} as const;

export type TestId = typeof TID[keyof typeof TID];

/** `[data-testid="<id>"]`, for a spec's locator or a test's querySelector. */
export function sel(id: TestId): string {
  return `[data-testid="${id}"]`;
}

/** The values of the Check step's tool select (`check-tool`), old and new. */
export const CHECK_TOOLS = ['pan', 'select', 'draw-line', 'rooms'] as const;
export type CheckTool = typeof CHECK_TOOLS[number];
