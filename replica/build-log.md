# Build log

| screen | date | status | missing | harder than expected |
| --- | --- | --- | --- | --- |
| shell (nav, layout, tokens, primitives, /design) | 2026-10-06 | done | | Next 16 writes AGENTS.md/CLAUDE.md on `next dev`; kept and extended |
| S01 Dashboard | 2026-10-06 | done | | |
| S02 Tracks | 2026-10-06 | done | | |
| S03 Track detail | 2026-10-06 | done | | |
| S04 Course detail | 2026-10-06 | done | | |
| S05 Player: slides | 2026-10-06 | done | recorded video (by design) | |
| S06 Player: coding | 2026-10-06 | done | persistent kernel (each run is a fresh process) | seeding random state before setup code so learner and solution see the same data |
| S07 Player: multiple choice (+ console) | 2026-10-06 | done | | |
| S08 Player: order / parsons / classify | 2026-10-06 | partial | classify uses group buttons, not drag | dnd-kit hydration ids |
| S09 Player: sequential | 2026-10-06 | done | iterative type | |
| S10 Chapter complete modal | 2026-10-06 | done | | |
| S11 Course complete | 2026-10-06 | done | | |
| S12 Progress | 2026-10-06 | done | XP-over-time chart | |
| S13 Outline drawer | 2026-10-06 | done | | |
| S14 Settings | 2026-10-06 | done | | |

All screens: no console errors, no horizontal overflow at 390px and 1440px
(checked with Playwright). Screenshots in `replica/clone-screens/`.

Content: 2 tracks, 16 course outlines (4 chapters each, no lessons yet), one
sample lesson in Python for Data Science / Python basics covering every
exercise type. Lessons are the lesson-builder agent's job.
