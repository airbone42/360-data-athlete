# Race pacing and load metrics — what CTL/TSB do and do not tell you

## TL;DR

CTL/ATL/TSB are *recent-load* signals from the fitness–fatigue model;
they predict **durability** (resistance to fatigue over long efforts),
not the **performance ceiling** of a short race. For races up to about
half-marathon distance (≲ ~90 min) the limiter is threshold / VO₂max /
running economy, which a trained athlete retains at modest CTL. Anchor
short-race pacing on **event demands + the athlete's race history +
quality base**, not on a low CTL number. CTL becomes a legitimate
pacing caveat only as event duration grows (≳ HM, multi-hour), where
durability and substrate depletion increasingly co-determine the result.

## Question / Trigger

A coach over-anchored a short-trail-race (~13–14 km, hilly) pacing
recommendation on a low current CTL ("base is low, hold back to Z3 early"),
despite the athlete's race history demonstrating sustainable
threshold-range efforts at *lower* fitness in prior build phases. The
athlete correctly challenged the recommendation as too conservative. This
document grounds the corrected rule (`framework/CLAUDE.md` → "No silent
conservatism" → pacing & race-strategy clause).

## Findings

### 1. What CTL/TSB actually model
CTL (Chronic Training Load) and ATL (Acute Training Load) are
exponentially-weighted moving averages of daily training load; TSB =
CTL − ATL. They operationalise the **Banister fitness–fatigue model**
(impulse–response). The output is a *form* estimate (freshness vs.
fatigue) and a *training-volume trend* — it is explicitly **not** a
direct measurement of VO₂max, lactate threshold, critical speed, or
running economy, which are the physiological determinants of race
performance. CTL is a proxy that correlates with fitness *when training
content is held roughly constant*; it says little about an experienced
athlete's retained high-intensity capacities after a volume dip.

### 2. Determinants of race performance are duration-dependent
The classic determinants of endurance performance are **VO₂max,
lactate/anaerobic threshold (or critical power/speed), and movement
economy** (Joyner & Coyle 2008). The *relative weight* of these shifts
with event duration:
- **Short to medium races (≈ ≤ HM, minutes to ~90 min):** the
  sustainable pace sits at or just below the lactate/critical-speed
  threshold. The limiter is *intensity-domain* physiology, which is
  preserved with relatively little volume and is trainable/retained via
  quality sessions even when CTL is modest.
- **Long races (≳ HM, multi-hour):** *durability* — the resistance of
  threshold, economy and VO₂ to decline over prolonged exercise —
  becomes a co-determinant. Durability is the capacity that genuinely
  tracks accumulated training volume (and therefore CTL). This is where
  a low CTL is a real pacing caveat.

### 3. Practical consequence for pacing recommendations
For a short race, an experienced athlete's **own race history** (recent
results, PRs, prior races run at comparable or lower fitness) is a
far better pacing anchor than a CTL number. A low CTL after a rebuild
does not move the threshold-anchored sustainable pace of a sub-90-min
race nearly as much as the volume drop implies. Over-conservative early
pacing ("hold Z3") then wastes the athlete's actual capacity and
produces a slower, not safer, race. Conservatism is warranted only for a
**named** reason — wellness red flag, an injury limiter on a *specific*
race demand (e.g. eccentric descent load on a reactive tendon → cap the
*downhill*, not the whole effort), or a documented taper freshness goal.

## Primary sources

- **Joyner, M.J. & Coyle, E.F. (2008).** "Endurance exercise
  performance: the physiology of champions." *Journal of Physiology*,
  586(1), 35–44. Establishes VO₂max, lactate threshold, and economy as
  the integrated determinants of endurance performance (paraphrased:
  sustainable race power/pace is set by the fraction of VO₂max usable at
  threshold and the economy of movement — not by training-volume
  metrics).
- **Jones, A.M. & Vanhatalo, A. (2017).** "The 'Critical Power' Concept:
  Applications to Sports Performance with a Focus on Intermittent
  High-Intensity Exercise." *Sports Medicine*, 47(S1), 65–78. Critical
  speed/power as the threshold that bounds sustainable pace for
  short-to-medium events.
- **Maunder, E., Seiler, S., Mildenhall, M.J., Kilding, A.E. &
  Plews, D.J. (2021).** "The Importance of 'Durability' in the
  Physiological Profiling of Endurance Athletes." *Sports Medicine*,
  51, 1619–1628. Introduces durability — decline of physiological
  thresholds during prolonged exercise — as a distinct, volume-dependent
  quality that matters most in long events.
- **Coggan, A. / Banister, E.W.** Performance Management Chart (CTL/ATL/
  TSB) — the fitness–fatigue impulse–response model. CTL/TSB are
  load-trend and form estimates, not direct fitness/performance
  measurements (foundational basis of the TrainingPeaks/intervals.icu
  PMC).

*Bibliographic details are accurate; the parenthetical "key finding"
lines are faithful paraphrases of each source's thesis, not verbatim
quotations.*

## Application in framework

- `framework/CLAUDE.md` → "No silent conservatism (mandatory)" → new
  pacing & race-strategy clause: forbids anchoring short-race pacing on
  CTL/recent-load; requires anchoring on event demands + athlete race
  history; requires a named trigger for any down-conservative pacing
  recommendation; injury limiters constrain the *specific demand*, not
  the whole effort. (Added 2026-06-03.)
- Athlete-specific race history and PRs that serve as the pacing anchor
  live in `config/athlete_static.md` and the activity/type history — not
  in the framework.

## Open questions / Caveats

- The ≤ ~90 min threshold for "short race" is a soft heuristic; the
  durability/CTL relevance rises continuously with duration, it does not
  switch on at HM distance.
- This document addresses *aerobic-endurance* race pacing. It does not
  cover technical-terrain tactics (line choice, power-hiking gradients,
  descent skill), which modulate *how* an effort is spent on trail but
  not the underlying sustainable-intensity ceiling.
- Heat, altitude, and fuelling can each independently force a more
  conservative pace and are separate from the CTL question.
