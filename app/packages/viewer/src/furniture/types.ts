// The furniture module's own state (furniture_boxes.js's kinds and pieces), shared by index.ts, boxes.ts, legend.ts and
// hover.ts. Owner: builder C. Not exported from the package.
import type { LineBasicMaterial, Mesh, MeshStandardMaterial } from 'three';
import type { FloorRecord, FurniturePiece } from '../contracts';
import type { RemovedGroup } from './logic';

export interface KindState {
  key: string;
  label: string;
  colour: string;
  /** mm, now (whole). */
  height: number;
  /** mm (whole): the underside above the floor of a piece standing on nothing. */
  base: number;
  /** mm (whole): the model's height; Reset goes back to it, `edited` means "differs from it". */
  defaultHeight: number;
  /** The kind's show tick. */
  visible: boolean;
  /** The kind's stops tick. */
  blocks: boolean;
  items: ItemState[];
  face?: MeshStandardMaterial;
  edge?: LineBasicMaterial;
}

export interface ItemState {
  d: FurniturePiece;
  kind: KindState;
  fl: FloorRecord;
  mesh: Mesh;
  /** The resolved underside above the floor level (mm). */
  z0mm: number;
  /** Ids of the doors and passages it stands in front of (a copy of the model's list, as strings). */
  approach: string[];
  /**
   * Deleted (docs/boxes/DESIGN.md 2.4): the mesh, the item and its place in the maps stay; the box is hidden, out of its
   * floor's colliders and out of its floor's 'late' list (boxes.ts setRemoved, syncKind).
   */
  removed: boolean;
}

/** A piece before its box exists (index.ts reads them, makeBoxes turns each into an ItemState with its mesh). */
export type PieceDraft = Omit<ItemState, 'mesh' | 'z0mm' | 'removed'>;

/** One step of the visit-long undo stack (docs/boxes/DESIGN.md 2.4): the ids a delete, a restore or Restore all changed. */
export interface UndoEntry { ids: string[]; dir: 'removed' | 'restored'; all: boolean }

/** What a change of the deleted boxes was, for the card, the toast and the legend line (after bus 'pieces'). */
export interface EditEvent {
  source: 'removed' | 'restored' | 'api';
  /** The ids whose state changed: the clicked or restored top first, then the furniture list's order. */
  ids: string[];
  /** The undo step this change pushed (it is the top of the stack), or null (an undo, setPieceEdits). */
  entry: UndoEntry | null;
  /** Restore all, or the undo of one. */
  all: boolean;
}

/** What the legend and the hover label need from the module (index.ts). */
export interface FurnitureState {
  kinds: KindState[];
  kindOf: Map<string, KindState>;
  items: ItemState[];
  itemOf: Map<string, ItemState>;
  /** The pieces that stand in the approach of a door or a passage. */
  inApproach: ItemState[];
  keepDoorways(): boolean;
  /** Whether a piece stops Walk now. */
  stops(p: ItemState): boolean;
  /** options.editBoxes: the staff app's version page (select, delete, restore). */
  editBoxes: boolean;
  /** The kinds that have a legend row: all of them with editBoxes, else the kinds with a live piece when the file loaded. */
  legendKinds: KindState[];
  /** The kind's pieces that are not deleted. */
  liveCount(k: KindState): number;
  removedIds(): ReadonlySet<string>;
  /** The deleted boxes as the Restore list's lines, in the furniture list's order. */
  groups(): RemovedGroup[];
  /** The top of the undo stack, or null. */
  undoTop(): UndoEntry | null;
  /** How many boxes the last Restore all brought back, while nothing was deleted or restored since; else 0. */
  restoredAll(): number;
  /** Called after every change of the deleted boxes (after bus 'pieces'). */
  onEdit(fn: (e: EditEvent) => void): void;
  /** The selection module's hooks (select.ts; null without editBoxes). */
  select: { cardOpen(): boolean; selectable(): boolean } | null;
}

/** The legend's actions (index.ts): what typing, the ticks and the buttons do. */
export interface LegendActions {
  setHeight(key: string, mm: number, keepText?: boolean): boolean;
  setVisible(key: string, on: boolean): boolean;
  setBlocks(key: string, on: boolean): boolean;
  setAllVisible(on: boolean): void;
  setKeepDoorways(on: boolean): boolean;
  reset(): void;
  saveCsv(): string;
  removePiece(id: string): string[];
  restorePiece(id: string): string[];
  restoreAll(): void;
  /** Undoes the last delete, restore or Restore all of this visit; false when there is none. */
  undo(): boolean;
}
