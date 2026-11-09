// The Check step's opening editor (docs/upload/DESIGN.md U-12.3, U-10.6): an opening clicked on the plan (or from its
// flag) -> its kind (door, window, passage, not an opening, or the detector's), head and sill -> settings.fixes.openings
// ({ floor, a, b as detected, kind, head, sill }), matched to the detector's record at the next build.
import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import type { OpeningFix, OverlayFloor } from '@/upload/contracts';
import { FieldRow, NativeSelect, NumberField } from './fields';

type Opening = OverlayFloor['openings'][number];
export const OPENING_KINDS: { value: OpeningFix['kind']; text: string }[] = [
  { value: null, text: "Keep the detector's" },
  { value: 'door', text: 'Door' },
  { value: 'window', text: 'Window' },
  { value: 'passage', text: 'Passage' },
  { value: 'none', text: 'Not an opening' },
];

export interface OpeningEditorProps {
  floor: string;
  opening: Opening;
  /** The fix already in the settings for this opening, if any. */
  fix: OpeningFix | null;
  disabled?: boolean;
  onApply: (fix: OpeningFix) => void;
  onClose: () => void;
}

export function OpeningEditor({ floor, opening, fix, disabled, onApply, onClose }: OpeningEditorProps) {
  const [kind, setKind] = useState<OpeningFix['kind']>(fix?.kind ?? null);
  const [head, setHead] = useState<number | null>(fix?.head ?? null);
  const [sill, setSill] = useState<number | null>(fix?.sill ?? null);
  useEffect(() => { setKind(fix?.kind ?? null); setHead(fix?.head ?? null); setSill(fix?.sill ?? null); }, [opening.id, fix]);
  const width = Math.hypot(opening.b[0] - opening.a[0], opening.b[1] - opening.a[1]);
  return (
    <section className="grid gap-3 rounded-lg border bg-background p-3 text-sm" data-testid="opening-editor" data-opening={opening.id}>
      <div className="flex items-center justify-between gap-2">
        <h4 className="font-semibold">{`Opening ${opening.id}`}</h4>
        <span className="text-xs text-muted-foreground">{`${opening.kind}, ${width.toFixed(2)} m${opening.flagged ? ', flagged' : ''}${opening.fixed ? ', fixed' : ''}`}</span>
      </div>
      <div className="grid grid-cols-3 gap-3">
        <FieldRow label="Kind">
          <NativeSelect value={kind ?? ''} disabled={disabled} data-testid="opening-kind"
            onChange={e => setKind((e.target.value || null) as OpeningFix['kind'])}>
            {OPENING_KINDS.map(k => <option key={k.text} value={k.value ?? ''}>{k.text}</option>)}
          </NativeSelect>
        </FieldRow>
        <NumberField label="Head" value={head} allowEmpty placeholder="computed" disabled={disabled || kind === 'none'} testId="opening-head" onCommit={setHead} />
        <NumberField label="Sill" value={sill} allowEmpty placeholder="computed" disabled={disabled || kind === 'none'} testId="opening-sill" onCommit={setSill} />
      </div>
      <div className="flex gap-2">
        <Button size="sm" disabled={disabled} data-testid="opening-apply"
          onClick={() => onApply({ floor, a: opening.a, b: opening.b, kind, head: kind === 'none' ? null : head, sill: kind === 'none' ? null : sill })}>
          Apply at the next build
        </Button>
        <Button size="sm" variant="ghost" onClick={onClose} data-testid="opening-close">Close</Button>
      </div>
    </section>
  );
}
