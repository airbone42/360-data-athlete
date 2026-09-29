# Running video clips — posterior setup and Garmin sections

Detail for running form checks: the posterior-clip setup rules of the
endurance specialist's film tip (`agents/specialist-endurance.md`) and the
`--garmin-sections` tokens the head coach passes to `analyse_video.py`
(CLAUDE.md, "Video form check (running)"). The agent keeps the core setup
rules in one paragraph; this file carries the full list with its reasons and
the section tokens with the choice by context. Read it when a posterior
running clip is prescribed or a running video is analysed.

## Posterior clips

**Posterior clips have their own setup rules — and one of them rules out
the obvious device.**

- **Do not prescribe a follow-me / moving camera for a frontal-plane
  question.** It is the natural choice and it does not work: against a
  fixed camera, six of eight markers — contralateral pelvic drop among
  them — fall to fair-to-poor rater agreement, and only foot-strike
  pattern and rearfoot position survive. This holds for body-relative
  markers too, so "reference and subject move together" is not a defence.
  Follow-me stays right for sagittal and overview clips.
- **Fixed camera, perpendicular to the plane of motion.** For a treadmill
  setup roughly 1.5 m distance and 1 m height is a documented starting
  point; overground, the distance has to be large enough that **both feet
  are visible in the same stance-phase frame**. Make that an explicit
  pre-clip check: where one leg fully occludes the other, a step-width or
  crossover question cannot be answered no matter how good the footage is
  — and a narrow gait *produces* exactly that occlusion, so the failure
  correlates with the finding.
- **Several independent passes in one session**, not one long sequence —
  a single pass with persistent occlusion yields nothing, while a handful
  of short passes give multiple independent contact events per side.
- **A comparison clip is run at the baseline's pace**, inside a narrow
  window. Step width narrows as speed rises: the direction is established,
  the magnitude at endurance paces is not measured anywhere, so the effect
  is eliminated rather than corrected for. The window width is a
  convention, not a literature figure — say so when prescribing it.
- **Scale rule for the report:** degrees from a posterior clip only for
  peak hip adduction. Everything else posterior is categorical.
- **Record the conditions when the baseline is set, not when it is
  compared** — surface, pace, position in the session, camera geometry. A
  baseline whose conditions are unknown cannot be compared against later,
  and that is discovered at the worst possible moment.

Sources and per-marker figures:
[posterior-video-running-marker-scale-and-setup.md](../research/posterior-video-running-marker-scale-and-setup.md).

## Garmin section types (`--garmin-sections`)

**Section types** (Garmin chooses suitable windows automatically):
Pass these tokens to `--garmin-sections` exactly as written (the script
accepts no translations):
- `frisch` (fresh) — first 30 % of the session, most stable segment
- `müde` (fatigued) — last 25 %, technique drift visible
- `bergauf` (uphill) — steepest available uphill (grade >4 %)
- `bergab` (downhill) — steepest downhill (especially relevant for
  achilles / trail)
- `stabil` (stable) — most consistent segment of the entire session
- `tempo` — fastest stable segment
- `easy` — easiest segment

**Decision by context:**
- Achilles issues → `frisch,bergauf,bergab` (foot strike on different
  terrain)
- Technique drift check → `frisch,müde` (compare start vs end)
- Trail focus → `frisch,bergauf,bergab`
- Standard form-check → `frisch,stabil,müde`

**Garmin data complements the video analysis:**
Video shows quality (technique); Garmin shows quantity (cadence, GCT,
VOS). Both are merged automatically when the activity ID is known.
