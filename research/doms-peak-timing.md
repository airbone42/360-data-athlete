# DOMS — peak timing, recovery window, 3-day validator window

**Created:** 2026-05-16

## TL;DR

1. **DOMS peaks at 24-72h, complete recovery 5-7 days.** Standard finding across sport science (Cheung 2003, Connolly 2003, Wikipedia/PMC).
2. **Mechanics:** microscopic muscle damage from eccentric contractions → inflammatory response → myofibrillar repair starts day 3, complete day 7.
3. **R004 validator rule (glute-DOMS NOTE in the last 3 days + hard glute exercises today = WARNING):** conservative and sensible — the 3-day window covers the peak range + early recovery start.
4. **Eccentric load as main trigger:** downhill running, heel drops, deep squats, RDL variants. Pure concentric load (cycling, concentric strength) hardly produces DOMS.
5. **"Eccentric" is not one category — separate ballistic from slow-eccentric.** The
   damage-relevant variables are eccentric time-under-tension per repetition and how
   close the muscle works to peak stretch, not the mere presence of a lengthening
   phase. A ballistic braking action (kettlebell-swing backswing, drop-jump landing,
   bounding) is an *overspeed eccentric* lasting well under a second per repetition
   and never reaching end-range; a slow high-amplitude excursion (RDL, Nordic curl,
   downhill running, heavy split squat) holds tension through a long lengthening
   range at or near peak stretch. The second class is the classic damage stimulus;
   the first sits closer to plyometrics. Practical consequence for spacing: treat the
   ballistic signature as a ~48 h stimulus and the slow-eccentric signature as a
   ≥ 72 h stimulus. Details and the running-economy caveat:
   [ballistic-hip-hinge-vs-eccentric-rdl-before-longrun.md](ballistic-hip-hinge-vs-eccentric-rdl-before-longrun.md).

## Findings

**DOMS timeline (Cheung K, Hume PA, Maxwell L. 2003. "Delayed onset muscle soreness: treatment strategies and performance factors." Sports Med):**

| Phase | Time after load | Mechanics |
|-------|-----------------|-----------|
| Asymptomatic | 0-12h | Acute neural fatigue + glycogen depletion; NO DOMS |
| Onset | 12-24h | First inflammatory markers + pain sensitivity begin |
| Peak | 24-72h | Maximum pain, largest strength loss (-20 to -30%) |
| Early recovery | 72-120h | Myofibrillar repair starts (day 3+) |
| Late recovery | 120-168h (5-7d) | Full function restored; repeated-bout adaptation established |

**Connolly DA, Sayers SE, McHugh MP (2003):** "Treatment and prevention of delayed onset muscle soreness." JSCR. Confirms the timeline + practical consequences for program periodisation.

**Sweet spot for highly eccentric workouts:**
- At least **48-72h spacing** between hard eccentric sessions on the same muscle group
- For Achilles phase 3 or given glute DOMS: 96h-120h
- Light-eccentric or concentric-only sessions can be inserted in between at 24h spacing

**Repeated-bout effect:**
After a first eccentric session, the second comparable session is markedly less DOMS-inducing (-30 to -50%). With regular exposure the adaptation stabilises — therefore: downhill intervals in the trail build phase are not only race-specifically useful, they also reduce the race-day DOMS risk.

## Primary sources

| Author / year | Title | Publisher / link | Key quote |
|---------------|-------|------------------|-----------|
| Cheung K, Hume PA, Maxwell L — 2003 | Delayed onset muscle soreness: treatment strategies and performance factors | Sports Medicine 33(2):145-164 | DOMS timeline + treatment options |
| Connolly DA, Sayers SE, McHugh MP — 2003 | Treatment and prevention of delayed onset muscle soreness | JSCR 17(1):197-208 | Practice synthesis with program recommendations |
| McHugh MP — 2003 | Recent advances in the understanding of the repeated bout effect | Scand J Med Sci Sports 13:88-97 | Repeated-bout-effect mechanics |
| Physiopedia | Delayed Onset Muscle Soreness | [physio-pedia.com](https://www.physio-pedia.com/Delayed_Onset_Muscle_Soreness) | Practitioner overview |
| Wikipedia (DOMS) | (reviews + citations) | [wikipedia.org](https://en.wikipedia.org/wiki/Delayed_onset_muscle_soreness) | Foundational overview of the literature |

## Application in framework

- **`framework/scripts/validate_plan.py` R004** — extend the header comment: "glute-DOMS NOTE in the last 3 days flag — DOMS peaks at 24-72h, recovery starts day 3. Conservative window avoids re-stress in the peak phase. Source: `framework/research/doms-peak-timing.md`."
- **Trail-downhill trigger:** if a downhill activity with > -10% gradient in the last 3 days + hard quad load planned today → WARNING (consistency extension).
- **Cross-reference** to [downhill-running-doms-taper.md](downhill-running-doms-taper.md) (M12) and [concurrent-training-interference.md](concurrent-training-interference.md) (M5).

## Open questions / Caveats

1. **DOMS-diagnosis NOTEs:** currently athletes must actively raise DOMS as a NOTE. An automatic detection (e.g. "eccentric-heavy session 24-72h ago" → DOMS-likely) would be an extension — not implemented yet.
2. **Cross-muscle-group DOMS:** a heavy leg session produces DOMS only in the loaded muscle groups (quad, glute). An R004 rule should be muscle-group-specific, not blanket — this is solved in the framework via tags and exercise classification.
3. **Masters athletes have a delayed DOMS peak** (possibly 36-96h instead of 24-72h). A conservative 96h-window variant would be more sensible for older athletes — currently not athlete-specifically configured.
