// The office select (docs/upload/DESIGN.md U-2 screen 2, U-8.4): the known offices (listOffices) + "New office...". On the
// New project page a new office is created by createProject (`newOfficeName`); on the Floors and Save steps of a project
// with no office it is named by its id (the slug of the name typed), which the API's office memory takes at save
// (contract-issues/U6.md U6-2: there is no route that makes an office by itself). In that 'settings' mode the select
// reports a change only when it names another office (a pick, or a typed name's id); "New office..." shows the name
// field and reports nothing until the name is given (UR, V3-1 / V3-2). Office names are text.
import { useQuery } from '@tanstack/react-query';
import { useEffect, useId, useState } from 'react';
import { Input } from '@/components/ui/input';
import { listOfficesOptions } from '@/api/generated/@tanstack/react-query.gen';
import { slugify } from '@/lib/slug';
import { NativeSelect } from './fields';

export const NEW_OFFICE = '__new__';

export interface OfficeChoice {
  /** An existing office id, or null. */
  office: string | null;
  /** A new office's name (office null), or null. */
  newOfficeName: string | null;
}

export interface OfficeSelectProps {
  value: OfficeChoice;
  onChange: (v: OfficeChoice) => void;
  disabled?: boolean;
  /** 'project': a new office is a name for createProject; 'settings': a new office becomes its id (the slug). */
  mode?: 'project' | 'settings';
  testId?: string;
  label?: string;
}

export function OfficeSelect({ value, onChange, disabled, mode = 'project', testId = 'office-select', label = 'Office' }: OfficeSelectProps) {
  const id = useId();
  const offices = useQuery(listOfficesOptions());
  const known = offices.data?.offices ?? [];
  // 'settings' mode keeps "New office..." here while its name is typed: the settings hold an office id or none, so the
  // choice is reported only once the name gives an id (UR, V3-2: the callers pass newOfficeName null, so the field never
  // showed and the select snapped back to "No office" after clearing the office)
  const [creating, setCreating] = useState(false);
  const isNew = mode === 'settings' ? creating : value.office === null && value.newOfficeName !== null;
  const [name, setName] = useState(value.newOfficeName ?? '');
  useEffect(() => { if (value.newOfficeName !== null) setName(value.newOfficeName); }, [value.newOfficeName]);
  // an office id in the settings that the list does not know (made from a typed name): shown as itself
  const unknownId = value.office !== null && !known.some(o => o.id === value.office) ? value.office : null;
  const selected = isNew ? NEW_OFFICE : value.office ?? '';
  const commit = () => {
    const oid = slugify(name, 63);
    if (!oid) return;
    setCreating(false);
    if (oid !== value.office) onChange({ office: oid, newOfficeName: null });
  };
  return (
    <div className="grid gap-1" data-testid={`${testId}-field`}>
      <label htmlFor={id} className="text-xs font-medium text-muted-foreground">{label}</label>
      <NativeSelect
        id={id}
        value={selected}
        disabled={disabled}
        data-testid={testId}
        onChange={e => {
          const v = e.target.value;
          if (mode === 'settings') {
            if (v === NEW_OFFICE) { setCreating(true); return; }
            setCreating(false);
            if ((v || null) !== value.office) onChange({ office: v || null, newOfficeName: null });
            return;
          }
          if (v === NEW_OFFICE) onChange({ office: null, newOfficeName: name });
          else onChange({ office: v || null, newOfficeName: null });
        }}
      >
        <option value="">No office</option>
        {known.map(o => <option key={o.id} value={o.id}>{o.name}</option>)}
        {unknownId && <option value={unknownId}>{unknownId}</option>}
        <option value={NEW_OFFICE}>New office...</option>
      </NativeSelect>
      {isNew && (
        <div className="grid gap-1">
          <Input
            className="h-8"
            placeholder="The office's name"
            value={name}
            disabled={disabled}
            data-testid="new-office-name"
            onChange={e => {
              setName(e.target.value);
              if (mode === 'project') onChange({ office: null, newOfficeName: e.target.value });
            }}
            onBlur={() => { if (mode === 'settings') commit(); }}
            onKeyDown={e => {
              if (mode !== 'settings' || e.key !== 'Enter') return;
              e.preventDefault();
              commit();
            }}
          />
          {mode === 'settings' && (
            <p className="text-xs text-muted-foreground">
              {slugify(name, 63) ? `Its id will be ${slugify(name, 63)}; its layer roles are remembered when the version is saved.` : 'Type a name with at least two letters or digits.'}
            </p>
          )}
        </div>
      )}
      {offices.isError && <p className="text-xs text-destructive">The offices could not be listed.</p>}
    </div>
  );
}
