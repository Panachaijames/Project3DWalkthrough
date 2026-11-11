// Converts the given files' CRLF line endings to LF (UR: Python's text-mode writes on Windows had turned LF files CRLF).
import { readFileSync, writeFileSync } from 'node:fs';

for (const f of process.argv.slice(2)) {
  const before = readFileSync(f, 'utf8');
  const after = before.replace(/\r\n/g, '\n');
  writeFileSync(f, after, 'utf8');
  console.log(`${f}: ${before.length - after.length} CR removed`);
}
