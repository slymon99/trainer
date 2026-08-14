# Decisions and evidence

The numbers this plan is anchored to and what would change them. Read it when
re-anchoring FTP, or when deciding whether the diagnosis still holds.

## FTP re-anchor log

Working FTP lives in intervals.icu sport settings. This records what it was set to,
when, and on what evidence.

| Date | Working FTP | Evidence |
|---|---|---|
| Jan 2026 | **270 W** | 270 W for 52 min on Alpe du Zwift. Genuine max; the last 20 min averaged 170 bpm, which is where LTHR comes from. |
| 13 Aug 2026 | 270 W — unchanged | 275 W proposed off two week-1 sessions completed at RPE 7. Rejected: both are prescribed sub-threshold, and their HR was proportional to their power rather than suppressed. A moderate session feeling moderate isn't evidence. |
| Sat 12 Sep 2026 | — | Next scheduled test. |

At each test, take intervals.icu's eFTP, set `ftp` and `indoor_ftp` together, and add
a row here.

## Power anchors

| Date | Effort | Notes |
|---|---|---|
| Jan 2026 | **270 W / 52 min** (Alpe du Zwift) | The FTP anchor. Repeatable, controlled, and the January reference every later Alpe test compares against. |
| Apr 2026 | **367 W / 4 min** | Completely empty at the end |
| Jun 2026 | 283 W / 16.6 min | Gran fondo |
| Aug 2026 | **279 W / 18 min**, avg HR 179 | Outdoor climb, 85°F at 74°F dew point, two weeks into riding after ~3 weeks off. intervals.icu read it as 265 W eFTP. Hot and undertrained, so plausibly an understatement — the block test settles it. |
| Aug 2026 | **917 W / 15 s** (best of 553 / 748 / 917 / 806) | Standing starts, indoor. Anchors the Wednesday sprint range. |

## Why LTHR is 170

intervals.icu derives LTHR as 91% of max HR by default, which gives 182 from a max HR
of 200 — and 200 is 7 bpm above anything ever recorded. That's a default off a wrong
input, not a measurement. It matters because a 12 bpm error shifts every HR zone
upward: a rep at 89% of true LTHR displays as 83%, i.e. easier than it was.

Audited against every ride back to Aug 2025:

| Evidence | Reading | Implied LTHR |
|---|---|---|
| **Highest HR ever recorded**, any ride | **193** | max ~194; the 200 in settings has never been seen |
| Jan 2026 Alpe, last 20 min of a 52-min max | 170 | **170** — textbook protocol, the strongest single point |
| Apr 2026 FTP test, 15 min | 173 | 163–170 |
| Aug 2026 climb, 18 min (hot) | 179 | 169–175, inflated by heat |
| Jun 2026 fondo, 16.6 min | 175 | 165–172 |
| Sep 2025 test, 30 min | 164 | 158–164 |

Nothing in 12 months supports 182. The longest he has *ever* averaged above 175 bpm
is 7.4 minutes, and the hardest 30-min efforts sit at 164–167; at LTHR 182 those would
run 185+. 170/193 is 88% of max, squarely inside the normal 85–92% band — 182 would be
94%, implausibly high.

**Confidence high, with 170 possibly 1–3 bpm generous.** LTHR is far more stable than
FTP, so an old measurement here isn't the concern an old FTP is. Forward test: the
12 Sep 20-min max should average 175–180. Below 172 means 170 is a couple high; above
183 reopens the question.

## The diagnosis, and what would refute it

**Fractional utilization is the limiter.** Don't read the ratio as "4-min power is
1.36× FTP" — flip it. FTP ÷ 4-min max = 270 / 367 = **73.5%**: how much of the aerobic
ceiling can be held for an hour. Trained cyclists sit at 75–85%, well-developed
endurance athletes at 80%+. And 367 W at 72 kg is 5.1 W/kg — solid, not remarkable.
So this is a *normal* ceiling on an underbuilt engine. The limiter is muscular
endurance and lactate clearance at threshold — mitochondrial density,
capillarization, holding sub-maximal work without drift — not VO2max. Even holding
the 4-min max constant, moving to a normal 78% ratio puts FTP at ~286 W: the goal is
already inside the existing ceiling.

*Hold that 73.5% loosely.* It divides a January FTP anchor by an April 4-min max,
three months and a fitness step apart, and the plan's own thesis is that the January
number was stale by April. At a true FTP of 278–282 the ratio is 76–77% — low-normal
rather than below the range. The direction is right; the number is softer than it
looks.

**Also underweight: chronic aerobic load.** Peak CTL 63 on 8–12 h/week available.

**On the VO2 work that isn't in this plan:** the spring's 5×4 min at 315 W was 86% of
a 367 W 4-min max, against a standard of 88–93%. That was extended threshold work in
a VO2 costume — too hard to be aerobic, too easy to stress VO2max. Almost no VO2
through December follows from the diagnosis, not from the sessions having failed.

**What would refute it**, worth checking at the October retest:

| Test | Refutes the diagnosis if |
|---|---|
| 3 h Z2 decoupling | Pw:Hr drift under 3% → the base is fine and it was purely a targets problem |
| 4-min max, October | Dropped below ~350 W → the VO2 dose was too low after all; add a session per fortnight in Block 4 |
| Block test | Comes in far above the working number → the plateau was substantially measurement artifact |
