# Decisions and evidence

The numbers this plan is anchored to and what would change them. Read it when
re-anchoring FTP, or when deciding whether the diagnosis still holds.

## FTP re-anchor log

Working FTP lives in intervals.icu sport settings (cycling id `953869`). This records
what it was set to, when, and on what evidence.

| Date | Working FTP | Evidence |
|---|---|---|
| Jan 2026 | **270 W** | 270 W for 52 min on Alpe du Zwift. Genuine max; the last 20 min averaged 170 bpm, which is where LTHR comes from. |
| 13 Aug 2026 | 270 W — unchanged | 275 W proposed off two week-1 sessions completed at RPE 7. Rejected: both are prescribed below threshold, and their HR was proportional to their power rather than suppressed. A moderate session feeling moderate isn't evidence. |
| **Sat 5 Sep 2026** | — | Next scheduled test: **Wachusett**, ~24-min max. See [`block-1.md`](block-1.md). |

At each test, take intervals.icu's eFTP, set `ftp` and `indoor_ftp` together, and add a
row here.

## Power anchors

| Date | Effort | Notes |
|---|---|---|
| Jan 2026 | **270 W / 52 min** (Alpe du Zwift) | The FTP anchor. Repeatable, controlled, and the January reference every later Alpe test compares against. |
| Apr 2026 | **367 W / 4 min** | Completely empty at the end |
| Jun 2026 | 283 W / 16.6 min | Gran fondo |
| Aug 2026 | **279 W / 18 min**, avg HR 179 | Outdoor climb, 85°F at 74°F dew point, two weeks into riding after ~3 weeks off. intervals.icu read it as 265 W eFTP. Hot and undertrained, so plausibly an understatement. |
| Aug 2026 | **917 W / 15 s** (best of 553 / 748 / 917 / 806) | Standing starts, indoor. Anchors the Wednesday sprint range. |

## Why the plan runs on ladders

Adopted 18 Aug 2026, from Tim Cusick's *Building Fatigue Resistance* (WKO4). The
governing principle — progress time-in-zone first, let watts follow at the test — was
already the plan's stated philosophy. What was missing was an actual progression to
follow, and the evidence that it was missing is this:

| Date | Session | Sweet spot rung |
|---|---|---|
| 14 Jan | 1×32 @ 91%, HR 162 | — |
| 24 Jan | 2×20 @ 90% | **2** |
| 11 Feb | 2×20 @ 88% | **2** |
| 19 Feb | 2×20 @ 89% | **2** |
| 12 Mar | 3×15 @ 90% | **3** |
| 30 Apr | 3×15 @ 89–91% | **3** |
| 14 May | 2×25 @ 89%, HR 153/150 | **4** |

**Sixteen weeks, two rungs, and it ended comfortable** — HR 150–153 on the last one is
88–90% of LTHR. Under the ladder rules that is about four weeks of work. The progression
then stopped entirely, and nothing above rung 4 has ever been ridden.

This is the concrete form of the plan's own diagnosis ("I progressed reps, never watts").
The correction isn't a new philosophy, it's a named next rung and a rule that a rung only
counts when it was completed at target.

**The intensity names also moved**, because the old ones were idiosyncratic: what the plan
called "sweet spot" (85–88%) is upper tempo everywhere else, and what it called
"sub-threshold" (89–94%) is what Coggan and Cusick both call sweet spot. Cusick prescribes
SST at 88–93%. The plan now uses four numbers — 85 / 90 / 97, plus easy — and no bands.

## Why LTHR is 170

intervals.icu derives LTHR as 91% of max HR by default, which gives 182 from a max HR of
200 — and 200 is 7 bpm above anything ever recorded. That's a default off a wrong input,
not a measurement. It matters because a 12 bpm error shifts every HR zone upward: a rep at
89% of true LTHR displays as 83%, i.e. easier than it was.

Audited against every ride back to Aug 2025:

| Evidence | Reading | Implied LTHR |
|---|---|---|
| **Highest HR ever recorded**, any ride | **193** | max ~194; the 200 in settings has never been seen |
| Jan 2026 Alpe, last 20 min of a 52-min max | 170 | **170** — textbook protocol, the strongest single point |
| Apr 2026 FTP test, 15 min | 173 | 163–170 |
| Aug 2026 climb, 18 min (hot) | 179 | 169–175, inflated by heat |
| Jun 2026 fondo, 16.6 min | 175 | 165–172 |
| Sep 2025 test, 30 min | 164 | 158–164 |

Nothing in 12 months supports 182. The longest he has *ever* averaged above 175 bpm is
7.4 minutes, and the hardest 30-min efforts sit at 164–167; at LTHR 182 those would run
185+. 170/193 is 88% of max, squarely inside the normal 85–92% band — 182 would be 94%,
implausibly high.

**Confidence high, with 170 possibly 1–3 bpm generous.** LTHR is far more stable than FTP,
so an old measurement here isn't the concern an old FTP is. **Forward test:** the Wachusett
max on 5 Sep should average 175–180. Below 172 means 170 is a couple high; above 183
reopens the question.

## Wachusett

The 5 Sep test and leaderboard attempt. Strava segment **16244804**, "Wachusett Mtn from
140 Climb" — 8,362 m, 370 m of gain, 4.4% average, a little rolling. It starts 33.6 mi
into the ride.

- **2025 reference:** 197 W over the segment, 30.0 min, HR 154 — a social ride, and the
  only Wachusett file in three years. He also stopped *inside* the segment and lost 421 s
  of elapsed time.
- **Leaderboard-derived targets:** 270–285 W ≈ 17th–22nd, 291 W ≈ 11th. Modelled at 82 kg
  all-in, Crr .006, CdA .32; the model back-solves plausible masses for 10 of the 11
  riders in 11th–22nd, so ±10 W. **These are watts, not `%FTP` — the same exception the
  Wednesday sprints get.**
- Modelled segment times at 82 kg: 197 W → 29.8 min *(actual was 30.0, so the model is
  within 1%)*, 250 W → 24.9, 275 W → 23.1, 300 W → 21.6, 325 W → 20.3, 350 W → 19.3. The
  extrapolation upward leans increasingly on the assumed CdA; treat the high end as ±1 min.
- **Approach handicap: 2–4%**, not the 5–8% the durability literature quotes. At ~160 W
  for 2h20 he oxidises roughly 63 g/h of carbohydrate, so absorbing 70–80 g/h of the 90
  taken in leaves endogenous glycogen use near zero. What remains is fluid loss and thermal
  strain, not depletion. Cutting the other way: durability is his named weakness, so he may
  sit at the worse end.

## The diagnosis, and what would refute it

**Fractional utilization is the limiter.** Don't read the ratio as "4-min power is 1.36×
FTP" — flip it. FTP ÷ 4-min max = 270 / 367 = **73.5%**: how much of the aerobic ceiling
can be held for an hour. Trained cyclists sit at 75–85%, well-developed endurance athletes
at 80%+. And 367 W at 72 kg is 5.1 W/kg — solid, not remarkable. So this is a *normal*
ceiling on an underbuilt engine. The limiter is muscular endurance and lactate clearance
at threshold — mitochondrial density, capillarization, holding sub-maximal work without
drift — not VO2max. Even holding the 4-min max constant, moving to a normal 78% ratio puts
FTP at ~286 W: the goal is already inside the existing ceiling.

*Hold that 73.5% loosely.* It divides a January FTP anchor by an April 4-min max, three
months and a fitness step apart, and the plan's own thesis is that the January number was
stale by April. At a true FTP of 278–282 the ratio is 76–77% — low-normal rather than below
the range. The direction is right; the number is softer than it looks.

**Also underweight: chronic aerobic load.** All-time peak CTL is **68.8 (28 Mar 2026)**,
with 65.1 on 6 Jul immediately before the three-week interruption. Modest for the hours
available, though less so than the 63 previously recorded here.

**Direct measurement of the limiter, 16 Aug 2026.** Durability blocks at 82–88% after 3 h
ran HR **154–158**, against 141–146 for the same percentages fresh three days earlier. A
+10–14 bpm cost at identical power is the fractional-utilization gap, measured rather than
inferred.

**On the VO2 work that isn't in this plan:** the spring's 5×4 min at 315 W was 86% of a
367 W 4-min max, against a standard of 88–93%. That was extended threshold work in a VO2
costume — too hard to be aerobic, too easy to stress VO2max. Almost no VO2 through
December follows from the diagnosis, not from the sessions having failed.

**What would refute it**, worth checking at the October retest:

| Test | Refutes the diagnosis if |
|---|---|
| 3 h Z2 decoupling | Pw:Hr drift under 3% → the base is fine and it was purely a targets problem |
| 4-min max, October | Dropped below ~350 W → the VO2 dose was too low after all |
| Block test | Comes in far above the working number → the plateau was substantially measurement artifact |
