// Small form fields of the Build page: a number or text field that keeps what is typed and commits on Enter or when it
// loses focus (one settings change per value, not per key), and a labelled row with one line of help. Text from
// drawings is passed as React text only.
import { useEffect, useId, useRef, useState, type ComponentProps, type ReactNode } from 'react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { cn } from '@/lib/utils';
import { parseNumber, showNumber } from './settingsEdit';

export function FieldRow({ label, help, children, htmlFor, className }: { label: ReactNode; help?: ReactNode; children: ReactNode; htmlFor?: string; className?: string }) {
  return (
    <div className={cn('grid gap-1', className)}>
      <Label htmlFor={htmlFor} className="text-xs text-muted-foreground">{label}</Label>
      {children}
      {help && <p className="text-xs text-muted-foreground">{help}</p>}
    </div>
  );
}

export interface NumberFieldProps {
  value: number | null;
  onCommit: (v: number | null) => void;
  /** An empty field commits null (else it goes back to the value). */
  allowEmpty?: boolean;
  disabled?: boolean;
  placeholder?: string;
  label?: ReactNode;
  help?: ReactNode;
  unit?: string;
  testId?: string;
  className?: string;
}

/** A metre value: typed as text ('3.7', '3,7', '0'), committed on Enter or blur. */
export function NumberField({ value, onCommit, allowEmpty = false, disabled, placeholder, label, help, unit = 'm', testId, className }: NumberFieldProps) {
  const id = useId();
  const [text, setText] = useState(showNumber(value));
  const focused = useRef(false);
  useEffect(() => { if (!focused.current) setText(showNumber(value)); }, [value]);
  const commit = () => {
    const v = parseNumber(text);
    if (v === null && !allowEmpty) { setText(showNumber(value)); return; }
    if (v !== value) onCommit(v);
  };
  const input = (
    <div className="flex items-center gap-1.5">
      <Input
        id={id}
        inputMode="decimal"
        className="h-8 w-24"
        value={text}
        disabled={disabled}
        placeholder={placeholder}
        data-testid={testId}
        onChange={e => setText(e.target.value)}
        onFocus={() => { focused.current = true; }}
        onBlur={() => { focused.current = false; commit(); }}
        onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); commit(); } }}
      />
      {unit && <span className="text-xs text-muted-foreground">{unit}</span>}
    </div>
  );
  return label === undefined ? input : <FieldRow label={label} help={help} htmlFor={id} className={className}>{input}</FieldRow>;
}

export interface TextFieldProps {
  value: string;
  onCommit: (v: string) => void;
  disabled?: boolean;
  placeholder?: string;
  label?: ReactNode;
  help?: ReactNode;
  testId?: string;
  className?: string;
  invalid?: boolean;
}

/** A text value committed on Enter or blur. */
export function TextField({ value, onCommit, disabled, placeholder, label, help, testId, className, invalid }: TextFieldProps) {
  const id = useId();
  const [text, setText] = useState(value);
  const focused = useRef(false);
  useEffect(() => { if (!focused.current) setText(value); }, [value]);
  const commit = () => { if (text !== value) onCommit(text); };
  const input = (
    <Input
      id={id}
      className="h-8"
      value={text}
      disabled={disabled}
      placeholder={placeholder}
      data-testid={testId}
      aria-invalid={invalid || undefined}
      onChange={e => setText(e.target.value)}
      onFocus={() => { focused.current = true; }}
      onBlur={() => { focused.current = false; commit(); }}
      onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); commit(); } }}
    />
  );
  return label === undefined ? input : <FieldRow label={label} help={help} htmlFor={id} className={className}>{input}</FieldRow>;
}

/** A native select (U-14.3: native selects, fast with hundreds of rows). */
export function NativeSelect({ className, ...props }: ComponentProps<'select'>) {
  return (
    <select
      className={cn(
        'h-8 rounded-md border border-input bg-transparent px-2 text-sm shadow-xs outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50',
        className,
      )}
      {...props}
    />
  );
}
