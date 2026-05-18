# Running cadence — 180-spm myth, self-selected ≈ optimal, +5% rehab protocol

**Created:** 2026-05-16

## TL;DR

1. **180 spm is a myth.** Jack Daniels observed 180 spm in Olympic runners at race pace in 1984 — never formulated as a universal target. Snyder & Farley 2011 show: in experienced runners self-selected cadence (typically 160-180 spm at moderate pace) ≈ energetically optimal.
2. **+5% of self-selected is the rehab protocol** (Heiderscheit 2011): reduces hip and knee loading + overstriding + impact forces, WITHOUT prescribing a specific cadence. Incremental adjustment individually.
3. **In the framework:** the Garmin 180-spm alarm was disabled in real application. training_paradigms.md already names the sources inline (Quinn 2019, van Oeveren 2017, Snyder & Farley 2011, Heiderscheit 2011, Bonacci 2018) — this doc persists them.
4. **Z2 easy pace with cadence < 170 is normal** and not a deficiency. Cadence targets belong in a rehab context (+5% with knee/IT-band issues), not as default coaching.

## Findings

**Origin of the myth:**
- Jack Daniels (1984 Olympic observation): top distance runners at race pace show ~180 spm
- → coach cult interpreted this as "180 spm is universally optimal"
- → Garmin/Polar etc. built 180-spm alarms as default

**What the studies actually say:**
- **Snyder & Farley 2011:** experienced runners have individually optimal cadence; self-selected usually corresponds to the energetically optimal
- **Heiderscheit 2011:** +5-10% from self-selected reduces joint loading — important rehab intervention. But: no specific absolute target (no "180")
- **Quinn 2019/2021:** cadence-adjustment training (10 days at 180 spm) reduced the metabolic cost in trained women — but the study design forced 180, was not a comparison with self-selected optimum
- **van Oeveren 2017:** cadence rises linearly with pace; at easy pace (Z2), 165-175 spm is completely normal, at race pace 175-185 spm
- **Bonacci 2018:** forefoot-vs-heel-strike mechanics influences cadence more than universal prescription

→ Consensus: cadence is **context-dependent** (pace, height, leg length, mechanics). Universal targets without context are methodologically wrong.

## Primary sources

| Author / year | Title | Publisher / link | Key quote |
|---------------|-------|------------------|-----------|
| Heiderscheit BC et al — 2011 | Effects of step rate manipulation on joint mechanics during running | Med Sci Sports Exerc 43(2):296-302 | +5-10% cadence reduces joint loading |
| Snyder KL, Farley CT — 2011 | Energetically optimal stride frequency in running | J Exp Biol 214:2089-2095 | Self-selected ≈ energy-optimal in experienced runners |
| van Oeveren BT et al — 2017 | Cadence Is a Determinant of Power-Velocity Relationships in Cycling and Running | (in movement literature) | Cadence rises linearly with pace; race pace > easy pace |
| Quinn TJ et al — 2021 | Cadence-adjustment training effects | (study replication) | 10 days @ 180 spm training lowers metabolic cost in trained women |
| Bonacci J et al — 2018 | Foot-strike pattern + cadence mechanics | (coach literature) | Strike pattern modifies cadence optimum |

## Application in framework

- **`config.example/training_paradigms.md`** lines 399-420 already cites the sources inline; this doc provides the persisted anchor.
- **The Garmin 180-spm alarm may be disabled** (athlete-specific override, see wrapper configuration) — sport-scientifically justified.
- **Rehab use case with IT-band or knee issues:** +5% from self-selected (Heiderscheit 2011) as a targeted intervention.
- **Cross-reference** to [strides-protocol.md](strides-protocol.md) (M13) — during strides cadence may briefly rise above 180 spm without concern.

## Open questions / Caveats

1. **Trail cadence** is lower than track cadence (technical footing, stabilisation pauses). 155-170 spm is often normal on trail.
2. **Overweight or obesity-reduction athletes** benefit from higher cadence (reduction of vertical oscillation + joint stress); the rehab protocol is more relevant here.
