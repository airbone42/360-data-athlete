# Passive vs. active dead hang — when is each indicated?

**Created:** 2026-05-19

---

## TL;DR

1. **Passive and active hang are NOT competitors — they are complementary
   variants with different therapeutic effects** and belong in the same
   programme. Passive hang = capsule stretch + joint decompression +
   subscapularis traction. Active hang = scapular depression + cuff
   activation (lower trapezius, serratus anterior). Active hang gives no
   capsule stretch; passive hang gives no cuff activation.
2. **Coach-literature default ("always active hang") is half-right.** It
   applies to healthy shoulders and to hypermobility (where passive
   hang stresses lax capsules). For capsular-restriction-pattern
   athletes (shoulder stiffness / frozen-shoulder-recovery / mild
   adhesion residual) passive hang is the therapeutically *indicated*
   variant — it does the work that scapular-AR exercises support
   long-term.
3. **Recommended sequence within a session (when both fit):** passive
   first → active second. Passive first decompresses + mobilises and
   prepares the joint; active second stabilises + strengthens. Default
   per-session split when 3 sets are programmed:
   - Capsular-restriction-pattern shoulder → **2 passive + 1 active**
   - Healthy shoulder → **1 passive + 2 active**
   - Hypermobility flag → **3 active** (passive contraindicated)
4. **Contraindications for passive hang:** hypermobility (laxity),
   active cuff inflammation, recent shoulder dislocation history, any
   acute shoulder pain that increases with traction. In those cases:
   active-only with controlled load, plus separate mobility work that
   isn't traction-based.

---

## Question / Trigger

The default coaching guidance for hanging exercises in the
calisthenics / grip-sport literature is "always active" (scapula
engaged, lower trap loaded). For rehabilitation populations with
capsular-restriction patterns — shoulder stiffness, adhesion residual,
frozen-shoulder recovery phase — that default produces under-dosed
mobility work. The framework needed a documented answer so the
specialist agents can prescribe the right per-set split by the
athlete's shoulder category.

Three concrete questions:

1. What are the distinct physiological effects of passive vs. active
   hang?
2. For which shoulder conditions is passive hang indicated, and for
   which contraindicated?
3. What's the recommended per-session split when both fit?

---

## Findings

### 1. Physiological differences (DeadHangs.com synthesis, GMB Fitness)

**Passive hang** — shoulders fully relaxed, "shoulder blades slide
upward and ears disappear between the upper arms":

- **Maximum spinal decompression** — "intradiscal pressure at L4-L5
  drops by 40-60% compared to standing" (DeadHangs.com)
- **Capsule stretch on the shoulder** — gives the acromion vertical
  space, traction on the glenohumeral capsule, loosens adhesions on
  the rotator cuff (Inspired By Sports / Primal Mobility)
- **Forearm flexor + grip dominant** — minimal active musculature
  above the elbow
- **No cuff activation** — lower trap + serratus stay quiet

**Active hang** — scapular engagement, shoulder blades pulled "down
and back while keeping arms straight":

- **Lower trapezius + serratus anterior** do most of the work — EMG
  shows significantly higher recruitment vs. passive (DeadHangs.com)
- **Scapular depression opens the subacromial space** — relieves
  impingement pattern by mechanically moving the acromion away from
  the cuff tendons
- **Muscular stabilisation** — trains the antagonist pattern to the
  upper-trap-shrug bias most desk-workers develop
- **No capsule stretch** — the joint stays compressed by the muscle
  engagement

### 2. Indications by shoulder condition

| Shoulder condition | Passive hang | Active hang |
|--------------------|--------------|-------------|
| Healthy shoulder, normal mobility | OK as variation, low priority | Default — builds scap control |
| Hypermobility / lax capsule | **Contraindicated** — stresses already-lax capsule | Required — builds compensatory stability |
| Capsular restriction / shoulder stiffness | **Indicated** — capsule stretch is the therapeutic target | OK as complement — adds stability |
| Impingement pattern (subacromial space narrow) | OK in moderation — subscapularis traction | **Indicated** — scap depression opens space |
| Acute cuff inflammation / recent injury | Avoid both until cleared | Avoid both until cleared |
| Post-dislocation history (capsule loose) | **Contraindicated** | Required, gradual progression |

The "always active" default is correct for hypermobility and
post-dislocation; it is half-right for healthy and impingement (active
is preferred but passive is OK as variation); it is **inverted for
capsular-restriction shoulders** where passive is the indicated
variant.

### 3. Per-session sequence and split

> "Passive hangs first to decompress and mobilize. Active hangs second
> to stabilize and strengthen." — DeadHangs.com synthesis

The reasoning: passive first warms the joint, increases ROM, loads the
capsule; active second uses that fresh ROM and adds the muscular
stabilisation pattern, locking in the gains. Reversing the order
(active first) primes the muscles to resist the passive stretch and
reduces the decompression effect.

**Default split by athlete category (3 sets programmed):**

| Athlete category (read from `athlete_static.md`) | Split |
|--------------------------------------------------|-------|
| Capsular restriction / shoulder stiffness | 2 passive + 1 active — emphasise the indicated mobility variant while keeping stability in the rotation |
| Healthy shoulder | 1 passive + 2 active — active default, passive as low-volume mobility insurance |
| Hypermobility flag | 3 active — passive contraindicated |

After 4–6 weeks of symptom-free progression in the capsular-restriction
case, the ratio can shift toward 1 passive + 2 active as the
restriction resolves and stability becomes the limiter.

**Single-set sessions:** active by default for all categories except
hypermobility-flagged (where active-only is the rule anyway). Add a
passive single-set on mobility-only days when the schedule allows.

### 4. GMB Fitness — progression sequence for new hangers

GMB emphasises gradual onboarding: assisted hangs (feet on floor for
partial bodyweight) → passive hangs (full bodyweight, shoulders
relaxed) → active hangs (full bodyweight + scap engagement). This is
the *introduction* sequence for athletes new to hanging, not the
within-session sequence — distinct from the passive-first /
active-second within-session order. Both sequences are compatible.

### 5. Why the "always active" coach-literature is widespread

The dominant calisthenics + grip-sport coaching audience is athletes
who want to progress toward pull-ups, muscle-ups, brachiation. For
that population:

- Active hang is the closer pre-requisite to the pull-up
  initiation pattern (scap depression before elbow flexion)
- Passive hang has no direct pull-up transfer
- Coaches optimise for the goal of "more pull-ups", not "shoulder
  capsule health"

That advice is correct for that audience but does not generalise to
rehab / capsular-restriction populations. The framework's
shoulder-rehab logic must override the calisthenics default when an
athlete's category warrants it.

---

## Application in framework

### What is changed / refined

1. **`agents/specialist-ninja.md` / `agents/specialist-complementary.md`:**
   When prescribing a multi-set Dead Hang block, choose the per-set
   split by the athlete's shoulder category as documented in their
   `config/athlete_static.md`:
   - Capsular restriction / shoulder stiffness → default 2 passive + 1
     active for 3-set blocks
   - Hypermobility flag → active-only, passive contraindicated
   - Healthy shoulder → default 1 passive + 2 active for 3-set blocks,
     active-only for 1-set sessions
   - Single-set block → active by default for all categories except
     hypermobility-flagged

2. **`config.example/athlete_static.md` template (when added):** a
   shoulder-category section with the three named flags
   (capsular-restriction / hypermobility / healthy / impingement) so
   the planner can read the category off a structured field instead of
   parsing free text.

3. **No new validator rule** — the choice is athlete-specific and
   judgement-driven, not mechanically detectable from the description
   text. Specialist judgement based on the shoulder-category flag is
   the enforcement point.

### What stays unchanged

- The shoulder-lock R002 validator behaviour (Pull-up + Klimmzug etc.
  blocked) — Dead Hang already has an exception
  (`dead\s*hang.*[2-5]\s*s`) in the regex; longer hangs pass via the
  bare-Zn check path.
- The Bar Traverse / Campus Board blocks remain — Dead Hang freedom
  doesn't extend to brachiation patterns.

---

## Open questions / Caveats

1. **Hypermobility test:** there is no explicit hypermobility flag in
   the framework's `config.example/athlete_static.md` template yet.
   For new wrapper users the planner should ask once whether the
   athlete tests positive on Beighton (≥ 4/9) before unlocking passive
   hang as a recurring element. Until that flag exists structurally,
   the safe default for unflagged athletes is active-only on multi-set
   blocks and a single passive trial set with explicit symptom-monitor
   instruction.
2. **Subacromial impingement vs. capsular restriction:** these can
   co-exist. If both signals are present, 1 passive + 2 active is the
   safer ratio (active emphasis for impingement, passive for capsule).
3. **Time-to-recheck:** if passive hang produces any new pain or
   weakness post-session for 2 sessions in a row, revert to active-
   only and re-evaluate (consider hidden hypermobility component or
   cuff sensitivity).
4. **Athletic transition:** when an athlete moves from rehab-pattern
   to performance-pattern (e.g. cleared to attempt pull-ups), the
   default split shifts to "active emphasis with passive as mobility
   maintenance" — typically 1 passive + 2 active or single-set active.

---

## Primary sources

| Author / publication | Title | Link | Key quote |
|----------------------|-------|------|-----------|
| DeadHangs.com | Dead Hang vs Active Hang: Differences, Benefits & When to Use Each | [deadhangs.com](https://deadhangs.com/passive-vs-active-hang/) | "Passive hangs first to decompress and mobilize. Active hangs second to stabilize and strengthen." + L4-L5 intradiscal pressure -40-60% under passive hang |
| GMB Fitness | Hanging Exercise For Shoulder Health | [gmb.io](https://gmb.io/hanging/) | "Start with assisted hangs … progress to passive hangs … then consider active hangs. Listen to your body and progress based on comfort." |
| Inspired By Sports | Dead Hang: The simplest exercise for shoulder health and grip strength | [inspiredbysports.com](https://www.inspiredbysports.com/en/dead-hang-the-simplest-exercise-for-shoulder-health-and-grip-strength/) | Passive hang loosens adhesions in rotator cuff + creates acromion space |
| The Conversation (Hush et al.) | What are dead hangs? Shoulder pain risks and safe execution | [theconversation.com](https://theconversation.com/what-are-dead-hangs-what-are-the-shoulder-pain-risks-and-how-do-i-do-them-safely-202346) | "Hanging completely passively can come with risk for those with shoulder hypermobility, and it's recommended to keep some active tone in your muscles as you hang." |
| Primal Mobility | Hang On: The Key to Shoulder Health | [primalmobility.com](https://www.primalmobility.com/blog/hanging) | Passive hang as decompression / capsule stretch primary indication |
