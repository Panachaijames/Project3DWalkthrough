import sys
sys.path.insert(0, 'services/builder')
from walkthrough_builder import losscheck as L
cases = [
    r'failed at C:\Users\x\AppData\Local\Temp\run\plan.dxf line 3',
    'see c:/data/projects/p/builds/b/out/model.json.',
    r'share \\server\share\folder\f.dwg here',
    'no path here',
    r'the converted drawing could not be opened: C:\Users\DWP2\Desktop\Project walkthrough\app\data\projects\bank-sampeng\builds\20261109T101500-0a1b2c\runs\0002-build\out\model.json',
    "[WinError 2] cannot find: 'C:\\\\Users\\\\DWP2\\\\Desktop\\\\Project walkthrough\\\\model.json'",
    r'C:\a\b.txt and also see logs/x',
    r'C:\Program Files\x\dwg2dxf.exe: error at C:\Temp\y z\input.dwg (3)',
    r'OSError: [Errno 13] Permission denied: C:\Users\DWP2\Desktop\Project walkthrough\app\data\x.json',
]
for c in cases:
    print(repr(c), '->', repr(L.scrub(c)))
