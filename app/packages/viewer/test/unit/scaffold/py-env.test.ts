// tools/lib.mjs pyEnv (fix step, 3 Nov code review): pytest run through tools/run-py.mjs writes its cache under the run's
// WT_TMP, or not at all; never services/api/.pytest_cache inside app/ (D-3). pyproject.toml is frozen, so the option goes
// in through PYTEST_ADDOPTS, which pytest splits with shlex (hence forward slashes in single quotes).
import { fileURLToPath, pathToFileURL } from 'node:url';
import { afterEach, describe, expect, it } from 'vitest';

type PyEnv = (extra?: Record<string, string>) => Record<string, string | undefined>;
const lib = async () => (await import(pathToFileURL(fileURLToPath(new URL('../../../../../tools/lib.mjs', import.meta.url))).href)) as { pyEnv: PyEnv };
const saved = { WT_TMP: process.env.WT_TMP, PYTEST_ADDOPTS: process.env.PYTEST_ADDOPTS };
afterEach(() => {
  for (const [k, v] of Object.entries(saved)) { if (v === undefined) delete process.env[k]; else process.env[k] = v; }
});

describe('pyEnv: the pytest cache', () => {
  it('goes under WT_TMP when it is set', async () => {
    process.env.WT_TMP = 'C:\\Users\\x\\AppData\\Local\\Temp\\wt-i';
    delete process.env.PYTEST_ADDOPTS;
    expect((await lib()).pyEnv().PYTEST_ADDOPTS).toBe("-o 'cache_dir=C:/Users/x/AppData/Local/Temp/wt-i/pytest-cache'");
  });
  it('is off without WT_TMP, and options already given are kept', async () => {
    delete process.env.WT_TMP;
    process.env.PYTEST_ADDOPTS = '-x';
    expect((await lib()).pyEnv().PYTEST_ADDOPTS).toBe('-x -p no:cacheprovider');
  });
});
