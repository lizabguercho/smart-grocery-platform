# DEV evaluation (scores on this split; see FROZEN.md for how to read them)

Scored titles: 100; pending/unscorable: 0. Same titles for every system.


## all (n=100)

| system | presence P / R / F1 | failed | joint entry P / R | exact title | false meas. on none | unit invented | unit F1 | role F1 | scope F1 |
|---|---|---|---|---|---|---|---|---|---|
| rules | 80% / 82% / 81% | 0 | 76% / 77% | 81/100 (73%-88%) | 9 | 0 | 100% | 100% | 100% |
| qwen | 91% / 91% / 91% | 1 | 35% / 39% | 68/100 (59%-77%) | 4 | 0 | 100% | 80% | 44% |
| cascade | 91% / 91% / 91% | 1 | 36% / 39% | 69/100 (60%-78%) | 4 | 0 | 100% | 80% | 44% |
| gpt4o | 98% / 100% / 99% | 0 | 78% / 82% | 91/100 (85%-96%) | 1 | 0 | 100% | 99% | 100% |

## labeled from scratch (n=56)

| system | presence P / R / F1 | failed | joint entry P / R | exact title | false meas. on none | unit invented | unit F1 | role F1 | scope F1 |
|---|---|---|---|---|---|---|---|---|---|
| rules | 71% / 76% / 73% | 0 | 68% / 72% | 39/56 (57%-80%) | 9 | 0 | 100% | 100% | 100% |
| qwen | 86% / 86% / 86% | 1 | 21% / 24% | 29/56 (39%-64%) | 4 | 0 | 100% | 68% | 39% |
| cascade | 86% / 86% / 86% | 1 | 22% / 24% | 30/56 (41%-66%) | 4 | 0 | 100% | 68% | 39% |
| gpt4o | 97% / 100% / 98% | 0 | 71% / 76% | 48/56 (75%-93%) | 1 | 0 | 100% | 97% | 100% |

## started from an assistant draft (n=44)

| system | presence P / R / F1 | failed | joint entry P / R | exact title | false meas. on none | unit invented | unit F1 | role F1 | scope F1 |
|---|---|---|---|---|---|---|---|---|---|
| rules | 100% / 93% / 97% | 0 | 93% / 87% | 42/44 (89%-100%) | 0 | 0 | 100% | 100% | 100% |
| qwen | 100% / 100% / 100% | 0 | 67% / 67% | 39/44 (77%-98%) | 0 | 0 | 100% | 100% | 80% |
| cascade | 100% / 100% / 100% | 0 | 67% / 67% | 39/44 (77%-98%) | 0 | 0 | 100% | 100% | 80% |
| gpt4o | 100% / 100% / 100% | 0 | 93% / 93% | 43/44 (93%-100%) | 0 | 0 | 100% | 100% | 100% |

## title exactly 24 chars (probably truncated) (n=26)

| system | presence P / R / F1 | failed | joint entry P / R | exact title | false meas. on none | unit invented | unit F1 | role F1 | scope F1 |
|---|---|---|---|---|---|---|---|---|---|
| rules | 100% / 64% / 78% | 0 | 89% / 57% | 20/26 (58%-92%) | 0 | 0 | 100% | 100% | 100% |
| qwen | 92% / 86% / 89% | 1 | 20% / 21% | 14/26 (35%-73%) | 1 | 0 | 100% | 58% | 31% |
| cascade | 92% / 86% / 89% | 1 | 20% / 21% | 14/26 (35%-73%) | 1 | 0 | 100% | 58% | 31% |
| gpt4o | 100% / 100% / 100% | 0 | 67% / 71% | 22/26 (69%-96%) | 0 | 0 | 100% | 100% | 100% |

## title not truncated (n=74)

| system | presence P / R / F1 | failed | joint entry P / R | exact title | false meas. on none | unit invented | unit F1 | role F1 | scope F1 |
|---|---|---|---|---|---|---|---|---|---|
| rules | 75% / 90% / 82% | 0 | 72% / 87% | 61/74 (74%-91%) | 9 | 0 | 100% | 100% | 100% |
| qwen | 90% / 93% / 92% | 0 | 42% / 47% | 54/74 (64%-82%) | 3 | 0 | 100% | 89% | 48% |
| cascade | 90% / 93% / 92% | 0 | 44% / 47% | 55/74 (65%-84%) | 3 | 0 | 100% | 89% | 48% |
| gpt4o | 97% / 100% / 98% | 0 | 84% / 87% | 69/74 (88%-99%) | 1 | 0 | 100% | 98% | 100% |

## Paired exact-title outcomes (all scored titles)

| pair | both correct | first only | second only | both wrong |
|---|---|---|---|---|
| rules vs qwen | 61 | 20 | 7 | 12 |
| rules vs cascade | 62 | 19 | 7 | 12 |
| qwen vs cascade | 68 | 0 | 1 | 31 |
