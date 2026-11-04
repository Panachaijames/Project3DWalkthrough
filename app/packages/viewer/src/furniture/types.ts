// The furniture module's own state (furniture_boxes.js's kinds and pieces), shared by index.ts, boxes.ts, legend.ts and
// hover.ts. Owner: builder C. Not exported from the package.
import type { LineBasicMaterial, Mesh, MeshStandardMaterial } from 'three';
import type { FloorRecord, FurniturePiece } from '../contracts';

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
}

/** A piece before its box exists (index.ts reads them, makeBoxes turns each into an ItemState with its mesh). */
export type PieceDraft = Omit<ItemState, 'mesh' | 'z0mm'>;

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
}
