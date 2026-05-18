# DFA-α1 — non-linear HRV index for threshold estimation

**Created:** 2026-05-16

## TL;DR

1. **DFA-α1 = 0.75 marks VT1 / aerobic threshold; DFA-α1 = 0.5 marks VT2 / anaerobic threshold.** Rogers et al. 2021/2024 as foundational studies; multiple validations in different populations (men, women, elite triathletes, cardiac patients).
2. **Reliability with power-output anchoring excellent:** HRVT1 ICC = 0.87, HRVT2 ICC = 0.97 (Frontiers 2024). Comparable with ventilatory and lactate methods — field-capable alternative to lab spirometry.
3. **Gap to athlete-specific field tests (see wrapper):** when a field-test HRVT1 deviates from a lab IAS, the explanation is generally either test conditions (treadmill calibration, warm-up effect) or drift of the lactate threshold over time. Both are plausible; a repeated test with a shorter interval to the lab anchor is the clean resolution.
4. **Application:** DFA-α1 is a non-invasive field-test anchor, but should **not** replace the primary zone-anchor construct (LTHR from a time trial). It serves as a secondary anchor for cross-validation.

## Findings

**Foundation:**
> "Absolute values of 0.75 and 0.5 of DFA α1 (HRVT1 and HRVT2, respectively) were positively associated with first (VT1) and second ventilatory thresholds (VT2), respectively, in a group of male recreational runners during an incremental treadmill test." (Rogers et al. 2021)

**Replication:**
- Women (Frontiers 2023): "DFA-alpha1-based thresholds showed good agreement with traditionally used thresholds"
- Elite triathletes: HRVT1 ≈ first lactate threshold in incremental bike tests
- Cardiac patients: strong correlations with VT1 in bike ramp tests

**Methodological requirements (Rogers et al.):**
- HR belt with high sampling rate (Polar H10 or comparable) — chest belt mandatory, wrist sensors unsuitable
- At least 2-min stable R-R interval recording per calculation window
- Sliding window 1-min with 30s update as standard real-time application
- Software: Kubios, HRV4Training (field), AI Endurance (own service)

**Caveats for your own test application:**
- Treadmill vs. outdoor: treadmill test is methodologically cleaner (controlled pace), but on uncalibrated belts the pace values lie 3-5% below the displayed value
- Warm-up: at least 10 min Z1 before test start; otherwise HRV values of the first step are unstable
- Fresh legs: 48h without intense load before the test

## Primary sources

| Author / year | Title | Publisher / link | Key quote |
|---------------|-------|------------------|-----------|
| Rogers B et al — 2021 | A New Detection Method Defining the Aerobic Threshold for Endurance Exercise and Training Prescription Based on Fractal Correlation Properties of Heart Rate Variability | [PMC 7845545](https://pmc.ncbi.nlm.nih.gov/articles/PMC7845545/) | DFA-α1 = 0.75 → VT1; r > 0.88 |
| Rogers B et al — 2021/2024 (extended) | Reliability and validity of a non-linear index of heart rate variability to determine intensity thresholds | [PMC 10875128](https://pmc.ncbi.nlm.nih.gov/articles/PMC10875128/) | ICC = 0.87 / 0.97 for HRVT1/HRVT2 |
| Doerr — 2021 (women validation) | Validation of a non-linear index of heart rate variability to determine aerobic and anaerobic thresholds during incremental cycling exercise in women | [PMC 9894976](https://pmc.ncbi.nlm.nih.gov/articles/PMC9894976/) | DFA-α1 also works for women |
| Schaffarczyk et al — 2021 | Real-Time Estimation of Aerobic Threshold … Olympic Triathlete | [PMC 8193503](https://pmc.ncbi.nlm.nih.gov/articles/PMC8193503/) | Practice application in single-case elite |
| Scientific Triathlon Podcast | DFA alpha-1: A non-invasive, cheap option for estimating the aerobic threshold with Bruce Rogers | [scientifictriathlon.com/tts329/](https://scientifictriathlon.com/tts329/) | Coach overview from Rogers himself |

## Application in framework

- **`config.example/training_paradigms.md`** "DFA-α1 section" (lines 90-110) already names Rogers 2021 + Doerr 2021 as sources; this doc provides the persistent anchor.
- **`config.example/zone_validation_protocol.md`** could introduce a DFA-α1 test as an additional validation stage after the time-trial LTHR test (cross-validation).
- **Athlete-specific DFA-α1 field tests** (see wrapper configuration) should be repeated under clearer test conditions when a larger gap to the lab anchor appears, to resolve the difference.

## Open questions / Caveats

1. **DFA-α1 as a primary zone anchor** is NOT recommended — time-trial LTHR remains the gold standard. DFA-α1 is a validation tool.
2. **Sport specificity:** DFA-α1 validations are primarily bike (cycling ergometer) and run (treadmill). Swim validation is missing.
3. **Activity-movement sensitivity:** DFA-α1 is sensitive to movement noise (gait pattern when running). On trail surfaces (technical footing) the method is less reliable than on track/treadmill.
