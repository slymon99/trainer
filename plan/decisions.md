# Decisions and corrections

Why the plan is the way it is, and what was tried and rejected. Newest first.

Read this when re-anchoring FTP, or when a rule in `plan.md` looks wrong — the odds
are it looked wrong before and the reason is here. It is not needed to prescribe a
week.

---

## 14 Aug 2026 — the plan was cut from 960 lines to a standing brief plus this folder

An adversarial review found the document contradicting itself in ways that would
change a prescription. The fixes, and what they cost:

**Rules that were deleted outright.** Session-based power bumping (the bonus rep
test, RPE-triggered target raises, the "fail a wattage twice" rule) and the
progress/repeat/back-off marker system. Two reasons. First, they were mutually
inconsistent: the rule for raising watts required a top session at an RPE *below*
what the same document said a correctly-executed top session should feel like, so
following both meant the watts could never rise — the exact 2026 failure, re-encoded.
Second, they ran on RPE, which resolves to about ±1. A week of training shouldn't
turn on whether a 7 got called an 8.

What replaces them: duration progresses within a block, watts progress at the block
test, and the weekly review is where judgement gets applied. Testing every 4–5 weeks
is what makes that safe — the 2026 failure was the same pattern running unbounded for
seven months.

**Absolute watts are gone.** The old document derived ~40 watt figures from the
working FTP and carried a checklist for updating all of them together, which made
re-anchoring — the single highest-value habit in the plan — expensive enough to
avoid. Everything is now `%FTP`, intervals.icu resolves it, and re-anchoring is one
API call. The lone exception is the Wednesday standing starts, which are ~3× FTP and
neuromuscular; deriving them from FTP would be meaningless.

**Contradictions resolved by deletion rather than arbitration:**

- The easy-ride ceilings were written unconditionally but were breached by three of
  the plan's own prescribed sessions — Sunday's blocks put 20 min above a 6-min cap,
  and the Wednesday sprints push a 70-min ride's NP past its cap. Now: one NP cap,
  explicitly scoped to the riding *around* prescribed blocks.
- "Hard day" had an in-ride definition and a post-ride definition that disagreed, and
  the consequences hung on the answer. One definition survives: IF ≥ 0.80 or TSS ≥ 220,
  scored afterward.
- A correctly executed threshold or VO2 session — RPE 8–9 by design — failed the
  "progress" test and scored a "repeat the week" marker. Block 1 hid this because
  everything in it is sub-threshold; it would have fired every week from Block 2.
- The heat section told you to *raise* watts if the derated target wasn't driving HR
  into its band. Heat raises HR at a given power, so that condition was nearly
  unreachable, and the case that actually happens had no rule. Also: Z2 HR ceilings
  were never heat-adjusted, so every hot outdoor ride breached one.
- "Every 4th week is a recovery week, non-negotiable" against blocks structured 4
  build + 1, i.e. every 5th. The rule is now a preference with a bound.
- Four different CTL-at-test figures and two different ramp rates, in one section
  that claimed to have already reconciled them. CTL targets now appear once, in
  `roadmap.md`; the arithmetic moved to `docs/reading-data.md` where the other load
  formulas live.

**Changed on physiological grounds, not consistency grounds:**

- Warm-up primers dropped from 105–110% to 100–105%. The priming effect the warm-up
  is buying scales with how far the work sits above aerobic steady state, so it's
  worth most before threshold and VO2 and little before sweet spot, where there isn't
  much oxygen deficit to prime away. 100–105% is sufficient for the former and
  proportionate before the latter. The diagnostic itself — rep 1 hard, reps 2–3 fine
  means insufficient warm-up — is unchanged and correct.
- Block 2 and 4 top sets reduced from 2×30 to 2×25. FTP is roughly 60-minute power;
  60 minutes of work at or above it with one break is a test, not a session, and
  would have been read as training.
- Fuelling numbers added. The plan justifies its best session as glycogen-depleted
  work without ever saying what to eat, which invites under-fuelling the exact
  sessions that matter most. Depletion is supposed to come from the 2.5–3 h in front
  of the blocks, not from the bottle.

**Estimates that were too precise for their evidence** were softened rather than
recomputed: the "+18 W is ~70% likely" figures, the cool-and-rested FTP
back-calculation (which stacked a heat correction and a detraining correction on one
field effort and produced two different ranges five lines apart), and the TSB
projections.

Section ordinals were dropped for plain headings. Only two calendar workouts cited
them; both were rewritten.

---

## 14 Aug 2026 — LTHR is 170, not 182. Resolved against the full activity history.

intervals.icu sport settings had FTP 268 / LTHR 182 / max HR 200. Now FTP and indoor
FTP both set correctly, LTHR 170, max HR 196.

The 12 bpm LTHR error was the serious one: it shifted every HR zone upward, so a rep
the plan reads as 89% of LTHR displayed there as 83% — easier than it was.

Audited every ride back to Aug 2025:

| Evidence | Reading | Implied LTHR |
|---|---|---|
| **Highest HR ever recorded**, any ride | **193** | max ~194; intervals.icu's 200 has never been seen |
| Jan 2026 ADZ, last 20 min of a 52-min max | 170 | **170** — textbook protocol, the strongest single point |
| Apr 2026 FTP test, 15 min | 173 | 163–170 |
| Aug 2026 climb, 18 min (hot) | 179 | 169–175, inflated by heat |
| Jun 2026 fondo, 16.6 min | 175 | 165–172 |
| Sep 2025 test, 30 min | 164 | 158–164 |

**Nothing in 12 months supports 182.** The longest he has *ever* averaged above 175
is 7.4 minutes. Hardest 30-min efforts sit at 164–167; at LTHR 182 those would run
185+.

**Where 182 came from:** 182 ÷ 200 = exactly 0.91 — intervals.icu's default
LTHR-as-%-of-max formula, applied to a max HR that is itself 7 bpm above anything
ever recorded. A derived default off a wrong input, not a measurement.

170/193 is 88% of max, squarely inside the normal 85–92% band; 182 would be 94%,
implausibly high. **Confidence high, with 170 possibly 1–3 bpm generous.** LTHR is
far more stable than FTP, so a 7-month-old measurement isn't the concern a
7-month-old FTP is. Forward test: the 12 Sep 20-min max should average 175–180.

---

## 13 Aug 2026 — proposed FTP 270 → 275. **Rejected.**

Worth recording because the argument was wrong in an instructive way, and the same
false positive would otherwise recur every week.

**The claim.** Week 1's two quality sessions both came in at RPE 7 with HR well under
the threshold expectations the document then carried:

| Session | Prescribed | Actual W | Actual HR | RPE |
|---|---|---|---|---|
| Tue 11 Aug, 3×12 | 245–250 W | 245 / 245 / 246 | 147 / 151 / 151 | 7 |
| Thu 13 Aug, 2×20 + 10 | 228–235 W | 229 / 228 / **240** | 141 / 144 / 146 | 7 |

**Why it doesn't hold.**

1. **Both sessions are specified sub-threshold.** Tuesday is described, verbatim, as
   "deliberately sub-threshold so it repeats weekly without digging a hole." RPE 7 is
   the design, not a deviation from it.
2. **The threshold HR ladder was applied outside its domain** — to a 12-minute rep at
   91%, when it was defined for 15–30 min reps at 95%+.
3. **HR was proportional, not suppressed.** Against the anchors the plan already
   trusts — Jan 52-min max at 100% FTP / 170 bpm, Aug 18-min max at 103% / 179,
   Tuesday's rep 3 at 91% / 151, Thursday at 84% / 141–144 — that's four points on one
   line. A consistent athlete, not one whose targets are 12 W light.
4. **The sweet-spot criterion was met, not exceeded.** "Could do one more rep but not
   two" was the spec; one more 20-min block was reported available. That's a
   correctly-targeted session, read backwards as an easy one.

**What survived:** Thursday's final block was ridden at 240 W, 8 W over target, at
RPE 7 — mild one-session evidence that the sweet spot target sat at the low end. Not
enough to move an anchor.

**The general lesson, which is the point of this entry: check what a session was
designed to feel like before reading how it felt as a signal.** A rule about sessions
that are designed to be hard, applied to a session designed to be moderate,
manufactures exactly the over-eager re-anchor it was meant to prevent. This still
applies to the weekly review even though the rule that triggered it has since been
deleted.

---

## 13 Aug 2026 — intensity vocabulary audit

"Threshold" had meant 91–100%, 91–93%, 95–102%, 96–102% and 100–103% in different
parts of the document, and **90% belonged to no zone at all** while the plan's anchor
session sat at 91%. That gap is what produced the false re-anchor signal above.

The zone table is now the only intensity vocabulary and every band is gapless. The
old "sweet spot straddles into tempo" special case for the Sunday blocks is gone —
they're simply sweet spot, ridden after 2.5 h, which is the entire point of the
session and needs no separate band.

---

## The 2026 diagnosis

The reasoning behind the whole plan, kept because a plan whose rationale silently
mutates can't be evaluated later.

**Fractional utilization is the limiter.** Don't read the ratio as "4-min power is
1.36× FTP" — flip it. FTP ÷ 4-min max = 270 / 367 = **73.5%**. That's how much of the
aerobic ceiling can be held for an hour. Trained cyclists sit at 75–85%, well-developed
endurance athletes at 80%+. 367 W at 72 kg is 5.1 W/kg — solid, not remarkable. So
this is a *normal* ceiling on an underbuilt engine: the gap is a low floor, not a high
roof. The limiter is muscular endurance and lactate clearance at threshold —
mitochondrial density, capillarization, holding sub-maximal work without drift. Not
VO2max. Even holding the 4-min max constant, moving to a normal 78% ratio puts FTP at
~286 W: the goal is already inside the existing ceiling.

*Caveat worth keeping in view:* that 73.5% divides a January FTP anchor by an April
4-min max, three months and a fitness step apart, and the plan's own thesis is that
the January number was stale by April. At the hypothesised 278–282 the ratio is
76–77% — low-normal rather than below the range. The diagnosis survives; the alarming
number is softer than it looks.

**Three compounding errors:**

1. **Never re-anchored.** FTP set in January, trained off through June. If it drifted
   to 282 by April, sweet spot at 240 W was 85% of true FTP rather than 89%, and VO2
   at 315 W was 112% rather than 117%. The training didn't stop working — it slid into
   maintenance while it kept being done. The single biggest error of the year.
2. **Reps progressed, watts never did.** Adding reps at fixed power raises
   time-in-zone, which is real until duration saturates. After that it's more fatigue
   for the same signal. Both progressions "ended feeling good" — a completed
   progression should end at the edge.
3. **VO2 targets were too low to be VO2 work.** 315 W is 86% of a 367 W 4-min max; the
   standard for 5×4 min is 88–93%. March–May was extended threshold work in a VO2
   costume: too hard to be aerobic, too easy to stress VO2max.
4. *(quieter)* Peak CTL 63 on 8–12 h/week available. Underweight for the hours.
   Chronic aerobic load is the untouched lever.

**Evidence that would refute this diagnosis**, worth revisiting at the October
retest:

| Test | Refutes the diagnosis if |
|---|---|
| 3 h Z2 decoupling | Pw:Hr drift <3% → base is fine, it was purely a targets problem |
| 4-min max, October | Dropped below ~350 W → the VO2 dose was too low after all |
| Block test | Comes in far above the working number → the plateau was substantially measurement artifact |
