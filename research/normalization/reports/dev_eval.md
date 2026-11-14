# DEV evaluation (development numbers, not test results)

Scored titles: 100; pending/unscorable: 0. Same titles for every system.


## all (n=100)

| system | presence P / R / F1 | failed | joint entry P / R | exact title | false meas. on none | unit invented | unit F1 | role F1 | scope F1 |
|---|---|---|---|---|---|---|---|---|---|
| rules | 80% / 82% / 81% | 0 | 51% / 52% | 70/100 (61%-79%) | 9 | 0 | 100% | 100% | 100% |
| qwen | 95% / 80% / 86% | 3 | 33% / 30% | 67/100 (58%-76%) | 2 | 0 | 100% | 54% | 57% |
| cascade | 95% / 86% / 90% | 0 | 43% / 41% | 72/100 (63%-81%) | 2 | 0 | 100% | 64% | 64% |

## labeled from scratch (n=56)

| system | presence P / R / F1 | failed | joint entry P / R | exact title | false meas. on none | unit invented | unit F1 | role F1 | scope F1 |
|---|---|---|---|---|---|---|---|---|---|
| rules | 71% / 76% / 73% | 0 | 42% / 45% | 31/56 (41%-68%) | 9 | 0 | 100% | 100% | 100% |
| qwen | 91% / 72% / 81% | 2 | 20% / 17% | 30/56 (41%-66%) | 2 | 0 | 100% | 38% | 38% |
| cascade | 92% / 79% / 85% | 0 | 30% / 28% | 33/56 (46%-71%) | 2 | 0 | 100% | 52% | 52% |

## confirmed assistant drafts (n=44)

| system | presence P / R / F1 | failed | joint entry P / R | exact title | false meas. on none | unit invented | unit F1 | role F1 | scope F1 |
|---|---|---|---|---|---|---|---|---|---|
| rules | 100% / 93% / 97% | 0 | 71% / 67% | 39/44 (77%-98%) | 0 | 0 | 100% | 100% | 100% |
| qwen | 100% / 93% / 97% | 1 | 57% / 53% | 37/44 (73%-93%) | 0 | 0 | 100% | 73% | 78% |
| cascade | 100% / 100% / 100% | 0 | 67% / 67% | 39/44 (77%-98%) | 0 | 0 | 100% | 80% | 80% |

## title exactly 24 chars (probably truncated) (n=26)

| system | presence P / R / F1 | failed | joint entry P / R | exact title | false meas. on none | unit invented | unit F1 | role F1 | scope F1 |
|---|---|---|---|---|---|---|---|---|---|
| rules | 100% / 64% / 78% | 0 | 67% / 43% | 18/26 (50%-85%) | 0 | 0 | 100% | 100% | 100% |
| qwen | 100% / 93% / 96% | 0 | 27% / 29% | 16/26 (42%-81%) | 0 | 0 | 100% | 47% | 47% |
| cascade | 100% / 93% / 96% | 0 | 27% / 29% | 16/26 (42%-81%) | 0 | 0 | 100% | 47% | 47% |

## title not truncated (n=74)

| system | presence P / R / F1 | failed | joint entry P / R | exact title | false meas. on none | unit invented | unit F1 | role F1 | scope F1 |
|---|---|---|---|---|---|---|---|---|---|
| rules | 75% / 90% / 82% | 0 | 47% / 57% | 52/74 (59%-80%) | 9 | 0 | 100% | 100% | 100% |
| qwen | 92% / 73% / 81% | 3 | 38% / 30% | 51/74 (58%-78%) | 2 | 0 | 100% | 58% | 62% |
| cascade | 93% / 83% / 88% | 0 | 52% / 47% | 56/74 (66%-85%) | 2 | 0 | 100% | 72% | 72% |

## Paired exact-title outcomes (all scored titles)

| pair | both correct | first only | second only | both wrong |
|---|---|---|---|---|
| rules vs qwen | 59 | 11 | 8 | 22 |
| rules vs cascade | 64 | 6 | 8 | 22 |
| qwen vs cascade | 67 | 0 | 5 | 28 |
