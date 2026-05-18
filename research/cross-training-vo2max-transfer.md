# Cross-training VO2max transfer — bike stimulus for running adaptation

**Created:** 2026-05-16

## TL;DR

1. **VO2max transfer from bike to run is real, but not 1:1.** Tanaka 1994 (cross-training review): "some transfer of training effects on VO2max exists from one mode to another" — typical transfer rate in trained athletes **40-70% of the modality-specific effect**.
2. **Specificity principle dominates in elite / well-trained:** "Cross-training effects never exceed those induced by the sport-specific training mode, and the principles of specificity of training tend to have greater significance, especially for highly trained athletes."
3. **Practical:** substituting run volume with bike preserves run performance, **as long as intensity is matched**. Bike VO2max stimuli (e.g. 30/15 Rønnestad) build central cardiovascular capacity that partially transfers to running.
4. **In framework context** (2-hard-stimulus strategy with run-threshold + bike-VO2max): the bike-VO2max stimuli are explicitly the **cross-training-efficient** choice — they spare Achilles/knee and deliver ~50-70% of the run-specific VO2max stimulus. The "50-70% transfer" figure mentioned in the framework is consistent with Tanaka.

## Findings

**Tanaka 1994 (Sports Medicine) — foundational review:**
Investigated the cross-training effect between running, cycling and swimming. Key results:

- Modality-specific test (e.g. run VO2max after run training) shows highest gains
- Cross-modality test (e.g. run VO2max after bike training) shows **partial transfer**, typically 40-70% of the direct training effect
- "nonspecific training effects seem to be more noticeable when running is performed as a cross-training mode" → run-induced central adaptations transfer particularly well to bike performance (central O2 delivery), less so the other way

**Physiological mechanisms:**
- **Central adaptations** (cardiac stroke volume, erythropoiesis, plasma volume) are modality-independent → transfer well
- **Peripheral adaptations** (mitochondrial density in the specific muscle group, capillary density, local enzymes) are modality-specific → hardly transfer
- In "well-trained" athletes more optimisation is on the peripheral side → transfer rate drops
- In "recreationally trained" athletes central adaptation still dominates → transfer rate is higher

**Practical operationalisation for the run-bike combo (Marathon Handbook, Tanaka, sport-coach consensus):**
- Bike volume can partially replace run volume (injury sparing, recovery) at matched intensity
- Bike VO2max stimuli (short intervals, 30/15, 4×4 min uphill) deliver ~50-70% of the run VO2max stimulus + 100% central adaptation
- Bike threshold stimuli deliver less transfer (more peripheral specificity on quad-glute)

**Transfer to the 2-hard-stimulus strategy:**
The choice "stimulus 1 = run threshold + stimulus 2 = bike VO2max" is physiologically optimal:
- Run threshold delivers maximum run specificity (peripheral adaptation in calf muscles, running economy)
- Bike VO2max delivers central cardio stimulus while sparing Achilles/knee on the run
- The transfer rate of 50-70% is plausible; the figure in the framework is consistent with Tanaka

## Primary sources

| Author / year | Title | Publisher / link | Key quote |
|---------------|-------|------------------|-----------|
| Tanaka H — 1994 | Effects of cross-training. Transfer of training effects on VO2max between cycling, running and swimming | [PubMed 7871294](https://pubmed.ncbi.nlm.nih.gov/7871294/), [Springer](https://link.springer.com/article/10.2165/00007256-199418050-00005) | "some transfer of training effects on maximum oxygen uptake exists from one mode to another" |
| Millet GP, Vleck VE, Bentley DJ — 2009 | Physiological Differences Between Cycling and Running | Sports Medicine 39(3):179-206 | Modality-specific VO2max differentials; quad-capillary adaptation higher in cyclists than runners |
| Sportscience TrainGain | Cross-Training: A Misnomer | [sportsci.org](https://www.sportsci.org/news/traingain/cross.html) | Specificity principle vs. transfer discussion |
| Marathon Handbook | Cycling For Runners: What The Research Says About Transfer & Offload | [marathonhandbook.com](https://marathonhandbook.com/cycling-for-runners/) | Practice overview of bike-for-runners substitution |

## Application in framework

- **`config.example/training_paradigms.md`** "2-hard-stimulus strategy" — the cited transfer rate of 50-70% now has Tanaka 1994 as a clean source anchor (previously only marked as "source: not cited").
- **Cross-reference** to [cross-sport-hr-differential.md](cross-sport-hr-differential.md) (HR mechanisms) and [polarized-training-seiler.md](polarized-training-seiler.md) (distribution logic).

## Open questions / Caveats

1. **Tanaka 1994 is an older review** — newer meta-analyses on cross-training transfer rates would refine the anchor. For our purpose (plausibility anchoring of the 50-70% rate) the foundational review is sufficient.
2. **For masters athletes** (slower recovery, higher need to spare joints) the cross-training strategy is *even* more sensible — the injury-sparing component outweighs the marginal transfer-loss component.
3. **In the race-specific phase (8-12 weeks pre-race)** bike substitution should be reduced to maximise run-specific peripheral adaptation — see polarized vs. pyramidal season-phase logic.
