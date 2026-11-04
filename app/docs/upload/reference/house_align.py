import pickle, sys, collections, statistics
D = pickle.load(open(sys.argv[1], 'rb')); items = D['items']
XS, YS = 68.171, 34.160
quad = lambda x, y: ('plan' if y <= YS else 'elev') + ('_left' if x < XS else '_right')
grid = collections.defaultdict(lambda: collections.defaultdict(list))
for d in items:
    if 'text' in d and 'GRID' in d['lay'].upper() and d['text'].strip():
        x, y = d['ins']; grid[quad(x, y)][d['text'].strip()].append((round(x, 3), round(y, 3)))
L, R = grid['plan_left'], grid['plan_right']
rows = []
for l in sorted(set(L) & set(R)):
    print(l, 'L', L[l], 'R', R[l])
# bank-style: first occurrence, median dx, dy
first = lambda G: {k: v[0] for k, v in G.items()}
fl, fr = first(L), first(R)
c = sorted(set(fl) & set(fr))
print('bank-style first-bubble median', statistics.median(fr[k][0] - fl[k][0] for k in c), statistics.median(fr[k][1] - fl[k][1] for k in c))
# orientation-aware: numbers = vertical lines (compare x), letters = horizontal (compare y)
dx = [statistics.median(x for x, _ in R[k]) - statistics.median(x for x, _ in L[k]) for k in c if k[0].isdigit()]
dy = [statistics.median(y for _, y in R[k]) - statistics.median(y for _, y in L[k]) for k in c if k[0].isalpha()]
print('numbers dx', sorted(round(v, 3) for v in dx)); print('letters dy', sorted(round(v, 3) for v in dy))
