// Grey furniture (docs/upload/DESIGN.md U-12.3): a family the furniture kit could not classify (kind `other`) gets a kind
// -> settings.furniture.words[kind] gains the family (and leaves any other kind). Family names are drawing text.
// "Remember for the office" per word is not offered: the settings and SaveBuildRequest carry no such flag
// (contract-issues/U6.md U6-3), so words stay with the project.
import type { BuildSettings } from '@/upload/contracts';
import { NativeSelect } from './fields';

/** The furniture kit's kinds (vendor/furniture_kit.py KINDS, in its legend order). */
export const FURNITURE_KINDS: { kind: string; label: string }[] = [
  { kind: 'atm', label: 'ATM / kiosk' }, { kind: 'computer', label: 'Computer / monitor' }, { kind: 'printer', label: 'Printer / copier' },
  { kind: 'phone', label: 'Telephone' }, { kind: 'tv', label: 'TV / wall screen' }, { kind: 'partition', label: 'Privacy screen / panel' },
  { kind: 'curtain', label: 'Curtain' }, { kind: 'lamp', label: 'Lamp' }, { kind: 'plant', label: 'Plant' },
  { kind: 'sanitary', label: 'Sanitary fitting' }, { kind: 'appliance', label: 'Appliance' }, { kind: 'bed', label: 'Bed' },
  { kind: 'seat', label: 'Chair / stool' }, { kind: 'sofa', label: 'Sofa / armchair' }, { kind: 'seat-back', label: 'Seat back' },
  { kind: 'table', label: 'Table / desk' }, { kind: 'coffee-table', label: 'Coffee / side table' }, { kind: 'bar-table', label: 'Bar table' },
  { kind: 'counter', label: 'Counter top' }, { kind: 'cabinet', label: 'Cabinet / casework' }, { kind: 'tall-cabinet', label: 'Tall cabinet / wardrobe' },
  { kind: 'other', label: 'Other furniture' },
];

/** The kind the settings give a family, or ''. */
export function kindOfFamily(s: BuildSettings, family: string): string {
  for (const [kind, words] of Object.entries(s.furniture.words)) if (words.includes(family)) return kind;
  return '';
}

export interface FurnitureWordsProps {
  families: { family: string; count: number | null }[];
  settings: BuildSettings;
  disabled?: boolean;
  focus?: string | null;
  onKind: (family: string, kind: string) => void;
}

export function FurnitureWords({ families, settings, disabled, focus, onKind }: FurnitureWordsProps) {
  if (!families.length) return null;
  return (
    <section className="grid gap-2 rounded-lg border bg-background p-3 text-sm" data-testid="furniture-words">
      <h4 className="font-semibold">Furniture of no known kind</h4>
      <p className="text-xs text-muted-foreground">Give a family a kind: its boxes take that kind's colour and height at the next build.</p>
      <ul className="grid gap-1">
        {families.map(f => (
          <li key={f.family} className="flex flex-wrap items-center gap-2" data-testid="furniture-family" data-family={f.family} data-focus={focus === f.family ? '' : undefined}>
            <span className="min-w-0 flex-1 truncate font-mono text-xs" title={f.family}>{f.family}</span>
            {f.count !== null && <span className="text-xs text-muted-foreground">{`${f.count} piece${f.count === 1 ? '' : 's'}`}</span>}
            <NativeSelect value={kindOfFamily(settings, f.family)} disabled={disabled} data-testid="furniture-word-kind"
              aria-label={`Kind of ${f.family}`} onChange={e => onKind(f.family, e.target.value)}>
              <option value="">No kind (grey)</option>
              {FURNITURE_KINDS.map(k => <option key={k.kind} value={k.kind}>{k.label}</option>)}
            </NativeSelect>
          </li>
        ))}
      </ul>
    </section>
  );
}
