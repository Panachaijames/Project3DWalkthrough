// Scaffold U0 (docs/upload/WORK_BREAKDOWN.md U0 step 6; DESIGN.md U-15.1): apps/web/src/upload/contracts.ts is a verbatim
// copy of docs/upload/upload-contracts.ts. A change goes into both (only the integration step changes a frozen file).
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const read = (rel: string) => readFileSync(fileURLToPath(new URL(rel, import.meta.url)));

describe('upload contracts copy', () => {
  it('equals docs/upload/upload-contracts.ts byte for byte', () => {
    const doc = read('../../../docs/upload/upload-contracts.ts');
    const copy = read('../src/upload/contracts.ts');
    expect(copy.length).toBeGreaterThan(10_000);
    expect(copy.equals(doc)).toBe(true);
  });
});
