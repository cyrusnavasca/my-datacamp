# Parity report: my-datacamp vs DataCamp (learning loop)

Date: 2026-10-06

**Verdict: shippable as a personal tool.** All 18 counted must-haves done,
feature score 93.8, no open S1/S2 bugs (5 found, 5 fixed, see `bugs.md`).
The real gap is not features but **content**: one sample lesson exists. The
lesson builder fills that.

| score | value |
| --- | --- |
| feature parity | 93.8 / 100 |
| must-haves | 18 / 18 (plus 2 clone-only must-haves, both done) |
| layout | not measured: recon used public sources only, no screenshots of the original were captured |
| unit tests | 25 / 25 |
| e2e tests | 30 / 30, axe scan clean on 14 screens, no overflow at 390px |

## Feature parity (from parity.py)

## Parity: 93.8 / 100

features 93.8  (34 counted, must-haves 18 of 18 done)

## By area, weakest first
- catalog                       90.0  (4 features)
- player                        92.0  (21 features)
- dashboard                    100.0  (1 features)
- progress                     100.0  (6 features)
- settings                     100.0  (1 features)
- design                       100.0  (1 features)

## Missing, in build order
- [should] player: DataFrame output as table, partial  (shown as text repr, not an HTML table)
- [should] player: Drag and drop: classify, partial  (click/keyboard group buttons instead of dragging cards)
- [could] catalog: Search across courses, no
- [could] player: Iterative exercise, no  (not built; sequential covers most uses)
- [could] player: SQL exercises, no

## Left out on purpose (not scored)
- DataCamp course content (videos slides exercises datasets): owned content; all lessons written fresh
- Recorded instructor video and audio: owned content and people
- Certifications: their credential network
- Teams and B2B admin: single user tool
- Leaderboards vs other users: the network
- Billing and premium gating: personal tool
- Mobile apps: personal local tool
- DataLab hosted notebooks: separate product
- DataCamp name logo mascot and copy: their brand

## Yours, not in the original (not scored)
- Content loaded from files a lesson-builder agent writes
- Content validation command
- Lesson-builder agent definition
- Notes per lesson

## Behaviour differences

| flow | original does | clone does | fix or keep |
| --- | --- | --- | --- |
| F03 run code | IPython session: state persists between runs, console accepts single commands | fresh Python process per run; script re-runs from the top, last expression echoed | keep for now; persistent kernel is next-step #2 |
| F03 run speed | warm session, near-instant | ~50 ms for plain Python, 1-3 s when importing pandas/sklearn/torch | same fix as above |
| F03 core loop | read, edit, Run, Submit: 2 clicks | same: 2 clicks, plus Ctrl/Cmd+Enter and Ctrl/Cmd+Shift+Enter | keep |
| F03 hint / answer | hint costs XP; answer after hint | same; -30% / -70% (exact original numbers unknown, from recon guess) | keep |
| F05 classify | drag cards into buckets | pick a group per item with buttons (keyboard and touch friendly) | keep; drag optional |
| lesson intro | recorded video with slides | markdown slides with math; no audio | keep (no presenter) |
| F01 resume | dashboard resume card | same, plus a daily goal and streak on the dashboard | keep |
| F09 content | authored in a CMS by instructors | YAML files, validated by `content:check`, written by an agent | yours |

## Top five to build next

1. **Lessons.** Run the lesson builder on Python for Data Science chapters 1-4, then pandas. Everything else is ready.
2. **Persistent Python kernel per exercise** so state carries over between runs and heavy imports happen once (matters a lot for PyTorch and transformers).
3. **DataFrame output as an HTML table** in the console (pandas `_repr_html_`), since half the DS track prints DataFrames.
4. **Install the AI track libraries** (`runner/requirements-ai.txt`) and add a fake LLM client helper to the harness for prompting lessons.
5. **Review mode / spaced practice**: re-serve exercises you needed hints on. Not in the original; worth more to you than parity.
