# HR anchors and the RPE band

Detail for the head-coach rule [No silent conservatism](../CLAUDE.md#no-silent-conservatism-policy):
stored %-anchors, and rehearsals that come back far easier than the band
predicts. CLAUDE.md keeps the rules, the anchor-marker syntax and the
recalibration threshold; this file carries the full derivation, the two
plausibility guards, the override semantics, the confounder list and how
the two audit checks behave. Read it when a historical %LTHR / %FTP anchor
is reused or re-derived, or when a rehearsal RPE sits far below its band.

**A stored percentage is only as good as the denominator it was computed
with.** When a past race's HR curve is filed as %LTHR (or a power curve as
%FTP), the threshold value **in force at the time of that race** belongs in
the same row. Otherwise the table ages silently: the denominator is revised
upward at the next validation, every percentage in the row becomes too low,
and every band derived from it inherits the deficit. The failure mode is
perverse — each threshold increase makes the derived prescription *more*
conservative, in the opposite direction to the athlete's development, and
nothing in the table looks wrong while it happens. Before reusing a
historical %-anchor, read the threshold stored on the source activity
itself and recompute.

**But the stored threshold is a datum too, and it can be the wrong one.**
A profile field carries whatever was configured at the time — often a lab
step-test value that was never race-validated, and step tests
systematically read below field threshold. Recomputing against it is not
automatically the correction; it can be the error. Two guards before
adopting a stored denominator:

1. **Plausibility beats provenance.** A percentage is only admissible if
   the resulting claim is physiologically possible. Threshold is by
   definition roughly one-hour sustainable, so an effort materially longer
   than an hour **cannot** average above it. When recomputing against the
   stored value produces an event average over 100 % LTHR for a
   90-minute race, the stored value is refuted — not the athlete's
   physiology. Sanity-check the output before trusting the input.
2. **"All-out" means short.** The cheapest tell of a drifted denominator
   is a max HR in the source race that is implausible against the
   threshold — *but only for a genuinely short all-out effort*, inside
   the hour the threshold is defined against. Over half-marathon distance
   and beyond, a well-paced race sits **at** threshold and peaks just
   under it; a max HR below LTHR is the expected shape there, not
   evidence. Applying the short-race tell to a long race argues for
   precisely the wrong correction.

**When the stored value is the wrong one, say so in the anchor rather than
quietly computing around it:** `[hr-anchor:<id> lthr=<used> stored=<field>
override=<reason>]`. The audit check then reports a declared override
(LOW) instead of drift, and the claim stays auditable — including the case
where the activity's stored value later changes, which invalidates the
override and is flagged separately.

*Enforcement: `audit_consistency.py::check_percent_anchors` (audit check
`PERCENT_ANCHORS`, online). Bind a stored %-anchor to its source activity
with a marker next to the table — `[hr-anchor:<activity-id> lthr=<value>]` —
and the check recomputes the claim against the `lthr` the activity itself
carries: a mismatch is HIGH (`percent_anchor_drift`), a `% LTHR (nnn)`
header with no anchor nearby is MEDIUM (`percent_anchor_missing`), and an
activity that cannot be fetched or carries no threshold is LOW rather than
silently passing. A deliberate departure from the stored value is declared
in the marker (`stored=` + `override=`) and reported as LOW
(`percent_anchor_override`); if the activity's own value later moves away
from the one the override was written against, that becomes MEDIUM
(`percent_anchor_override_stale`). The max-HR tell is only cited for
efforts inside `_ALL_OUT_MAX_SECONDS`; on longer races the check says
explicitly that the peak does **not** refute the denominator. Tests:
`tests/test_percent_anchors.py`.*

**A rehearsal that comes back far easier than the band predicts is evidence
against the band.** When an exposure run at the prescribed race band returns
an RPE well below expectation, the first hypothesis is that the prescription
is wrong — not that the athlete is unusually fresh or has gained form.
Rehearsals executed inside a faulty band cannot falsify it; they reproduce
it, and their HR ceilings then read as confirmation. That makes the
subjective signal the only independent evidence available before the race
itself. Treat a persistent RPE-below-expectation at the prescribed band as a
trigger to re-derive the band, not as a note about form.

**"Well below expectation" is a measured quantity, not a coach's
impression** — and it is a larger gap than intuition suggests. The evidence
supports only a corridor about two CR10 points wide, with a between-athlete
SD near one point and a test-retest SEM up to one point, so a session that
feels "a bit easier than planned" is inside the noise and says nothing. A
report two points under the corridor floor is the smallest defensible
suspicion; three points at once, or two points twice inside 14 days, is the
band-recalibration signal. Read the reverse direction differently: an RPE
above the corridor is a readiness signal that belongs in the HRV/RHR
overload path, not a reason to touch the band. Derivation, sources and the
confounder list (heat, cardiac drift, outdoor vs. treadmill, caffeine,
blocks under 8 min, HR data quality):
[rpe-vs-percent-lthr-endurance-run.md](../research/rpe-vs-percent-lthr-endurance-run.md).

*Enforcement: `audit_consistency.py::check_rpe_hr_discrepancy` (audit check
`RPE_HR_DISCREPANCY`, online) with the pure logic in
`app/utils/band_rpe.py`. It compares the peak sustained 8-minute HR window
of a qualifying block — session averages hide a short block inside an easy
hour — against the RPE reported for that day, and only where attribution is
unambiguous: exactly one quality session and exactly one reported value.
Know its blind spot before reading silence as an all-clear: in the
threshold bands outdoors the corridor is discounted twice, which leaves the
check close to unreachable there. Tests: `tests/test_band_rpe.py`,
`tests/test_rpe_hr_discrepancy_check.py`.*
