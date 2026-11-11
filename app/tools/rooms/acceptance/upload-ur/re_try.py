import re
t = 'share \\server\share\folder\f.dwg here'
print(repr(t))
for pat in [r'\\', r'(?:[A-Za-z]:\|\\)', r'(?:[A-Za-z]:\|\\)(?:[^\/\r\n:"\'<>|*?]*\)*',
            r'(?:(?:[A-Za-z]:\|\\)(?:[^\/\r\n:"\'<>|*?]*\)*|[A-Za-z]:/(?:[^\/\r\n:"\'<>|*?]*/)*)[^\s\/"\'<>|*?]*']:
    print(pat, [m.group(0) for m in re.finditer(pat, t)])
