"""Verifier experiment: dwgread's exit code and the end of its JSON on the project's drawings (read-only)."""
import shutil
import subprocess
import sys
from pathlib import Path

APP = Path.cwd()
ROOT = APP.parent
lib = APP / 'vendor' / 'libredwg-0.14-win64'
work = Path(sys.argv[1])
work.mkdir(parents=True, exist_ok=True)
for name in sys.argv[2:]:
    dst = work / 'input.dwg'
    shutil.copyfile(ROOT / name, dst)
    p = subprocess.Popen([str(lib / 'dwgread.exe'), '-O', 'JSON', 'input.dwg'], cwd=str(work), stdout=subprocess.PIPE,
                         stderr=subprocess.DEVNULL)
    n = 0
    last = b''
    for line in p.stdout:
        n += 1
        if line.strip():
            last = line
    code = p.wait()
    print(f'{name}: exit {code:#x}, {n} lines, last line {last[:40]!r}')
