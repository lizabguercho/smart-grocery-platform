# TEST2 evaluation (scores on this split; see FROZEN.md for how to read them)

Scored titles: 100; pending/unscorable: 0. Same titles for every system.


## all (n=100)

| system | presence P / R / F1 | failed | joint entry P / R | exact title | false meas. on none | unit invented | unit F1 | role F1 | scope F1 |
|---|---|---|---|---|---|---|---|---|---|
| rules | 81% / 64% / 72% | 0 | 28% / 22% | 45/100 (35%-54%) | 9 | 0 | 86% | 74% | 74% |
| qwen | 89% / 92% / 90% | 1 | 17% / 22% | 47/100 (37%-56%) | 7 | 0 | 75% | 76% | 72% |
| cascade | 89% / 95% / 92% | 1 | 19% / 25% | 49/100 (39%-58%) | 7 | 0 | 76% | 76% | 72% |
| gpt4o | 92% / 100% / 96% | 0 | 38% / 46% | 63/100 (53%-72%) | 5 | 0 | 88% | 86% | 74% |

## labeled from scratch (n=48)

| system | presence P / R / F1 | failed | joint entry P / R | exact title | false meas. on none | unit invented | unit F1 | role F1 | scope F1 |
|---|---|---|---|---|---|---|---|---|---|
| rules | 81% / 81% / 81% | 0 | 19% / 19% | 12/48 (12%-38%) | 7 | 0 | 85% | 62% | 67% |
| qwen | 86% / 89% / 88% | 1 | 12% / 17% | 13/48 (15%-40%) | 5 | 0 | 80% | 61% | 48% |
| cascade | 87% / 92% / 89% | 1 | 13% / 19% | 14/48 (17%-42%) | 5 | 0 | 81% | 62% | 49% |
| gpt4o | 88% / 100% / 94% | 0 | 16% / 22% | 15/48 (19%-44%) | 5 | 0 | 85% | 78% | 60% |

## started from an assistant draft (n=52)

| system | presence P / R / F1 | failed | joint entry P / R | exact title | false meas. on none | unit invented | unit F1 | role F1 | scope F1 |
|---|---|---|---|---|---|---|---|---|---|
| rules | 82% / 39% / 53% | 0 | 55% / 26% | 33/52 (50%-77%) | 2 | 0 | 100% | 100% | 86% |
| qwen | 92% / 96% / 94% | 0 | 28% / 30% | 34/52 (52%-79%) | 2 | 0 | 88% | 100% | 95% |
| cascade | 92% / 100% / 96% | 0 | 31% / 35% | 35/52 (54%-81%) | 2 | 0 | 89% | 100% | 95% |
| gpt4o | 100% / 100% / 100% | 0 | 83% / 83% | 48/52 (85%-98%) | 0 | 0 | 100% | 100% | 95% |

## random part (population) (n=60)

| system | presence P / R / F1 | failed | joint entry P / R | exact title | false meas. on none | unit invented | unit F1 | role F1 | scope F1 |
|---|---|---|---|---|---|---|---|---|---|
| rules | 67% / 76% / 71% | 0 | 54% / 62% | 44/60 (62%-83%) | 8 | 0 | 89% | 90% | 90% |
| qwen | 71% / 81% / 76% | 1 | 40% / 48% | 42/60 (58%-82%) | 7 | 0 | 85% | 87% | 94% |
| cascade | 73% / 90% / 81% | 1 | 44% / 57% | 44/60 (62%-83%) | 7 | 0 | 87% | 88% | 94% |
| gpt4o | 84% / 100% / 91% | 0 | 52% / 62% | 48/60 (70%-88%) | 4 | 0 | 88% | 80% | 76% |

## targeted part (stress) (n=40)

| system | presence P / R / F1 | failed | joint entry P / R | exact title | false meas. on none | unit invented | unit F1 | role F1 | scope F1 |
|---|---|---|---|---|---|---|---|---|---|
| rules | 96% / 58% / 72% | 0 | 0% / 0% | 1/40 (0%-8%) | 1 | 0 | 81% | 68% | n/a |
| qwen | 100% / 97% / 99% | 0 | 6% / 8% | 5/40 (2%-22%) | 0 | 0 | 67% | 76% | 59% |
| cascade | 100% / 97% / 99% | 0 | 6% / 8% | 5/40 (2%-22%) | 0 | 0 | 67% | 76% | 59% |
| gpt4o | 97% / 100% / 99% | 0 | 30% / 37% | 15/40 (22%-52%) | 1 | 0 | 83% | 88% | 65% |

## title exactly 24 chars (probably truncated) (n=23)

| system | presence P / R / F1 | failed | joint entry P / R | exact title | false meas. on none | unit invented | unit F1 | role F1 | scope F1 |
|---|---|---|---|---|---|---|---|---|---|
| rules | 91% / 71% / 80% | 0 | 36% / 29% | 12/23 (30%-70%) | 1 | 0 | 72% | 75% | 67% |
| qwen | 100% / 100% / 100% | 0 | 25% / 29% | 13/23 (35%-74%) | 0 | 0 | 57% | 83% | 92% |
| cascade | 100% / 100% / 100% | 0 | 25% / 29% | 13/23 (35%-74%) | 0 | 0 | 57% | 83% | 92% |
| gpt4o | 88% / 100% / 93% | 0 | 35% / 43% | 13/23 (35%-74%) | 2 | 0 | 61% | 73% | 75% |

## title not truncated (n=77)

| system | presence P / R / F1 | failed | joint entry P / R | exact title | false meas. on none | unit invented | unit F1 | role F1 | scope F1 |
|---|---|---|---|---|---|---|---|---|---|
| rules | 78% / 62% / 69% | 0 | 25% / 20% | 33/77 (31%-53%) | 8 | 0 | 88% | 75% | 78% |
| qwen | 85% / 89% / 87% | 1 | 15% / 20% | 34/77 (32%-55%) | 7 | 0 | 80% | 76% | 64% |
| cascade | 86% / 93% / 89% | 1 | 17% / 24% | 36/77 (36%-57%) | 7 | 0 | 80% | 77% | 66% |
| gpt4o | 94% / 100% / 97% | 0 | 38% / 47% | 50/77 (55%-75%) | 3 | 0 | 96% | 89% | 75% |

## Paired exact-title outcomes (all scored titles)

| pair | both correct | first only | second only | both wrong |
|---|---|---|---|---|
| rules vs qwen | 39 | 6 | 8 | 47 |
| rules vs cascade | 41 | 4 | 8 | 47 |
| qwen vs cascade | 47 | 0 | 2 | 51 |
