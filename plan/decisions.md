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
| 25 Aug 2026 | **249 W / 55 min**, avg HR 152 | Indoor, submaximal — sweet spot rung 5 ridden long. 92% of the working FTP at 89% of LTHR, flat, and he finished feeling good. Compare 14 Jan: 246 W for 32 min at HR 162. Same relative power, 23 min longer, 10 bpm lower. |
| Aug 2026 | **917 W / 15 s** (best of 553 / 748 / 917 / 806) | Standing starts, indoor. Anchors the Wednesday sprint range. |

## Why the plan runs on ladders

Adopted 18 Aug 2026, from Tim Cusick's *Building Fatigue Resistance* (WKO4), the
deck itself kept in [`sources/`](sources/wko4-fatigue-resistance.md). The
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

**Target: 285 W, band 278–293.** These are watts, not `%FTP` — the same exception the
Wednesday sprints get. Triangulated three ways: the Jan 52-min max of 270 W implies a
24-min max of 284–297 W as of January; the Aug 18-min at 279 W in 74°F dew heat-corrects
to ~295 W for 18 min; and the 25 Aug 1×55 at 249 W / HR 152 implies hour power of
278–288 W, so a 22–24 min max near 294–300 W fresh. Less the approach handicap below.

### Converting watts to a segment time

**The leaderboard is scored in time, so don't model rivals' watts.** Read the 10th-place
elapsed time off the board and convert it here. Back-solving plausible masses for the
riders above him adds a free parameter per rider and lands 20–30 W high.

**The only trustworthy calibration input is his own 2025 file** — same road, same bike,
same power meter. Two models bracket the answer, and the gap between them is mostly
whether that social ride carried a draft:

- **Raw physics**, race setup after the stop: 80.5 kg all-in, Crr .005, CdA .30, ρ 1.18,
  drivetrain 97.5%.
- **Scaled to the 2025 file**, forcing 197 W → 30.0 min. That needs a 8.1% correction,
  i.e. he was 8% faster in 2025 than the raw inputs predict.

| His power | Raw physics | Scaled to 2025 file |
|---|---|---|
| 275 W | 23.4 min | 22.1 min |
| **285 W** | **22.8 min** | **21.5 min** |
| 295 W | 22.2 min | 20.9 min |
| 300 W | 21.9 min | 20.7 min |

Inverted: **23.0 min costs him 261–282 W, 22.0 min costs 276–299 W.** So a top-10 time
near 23 min is comfortably inside the 285 W target, and 300 W is not required for it.

**Approach handicap: 2–4%**, not the 5–8% the durability literature quotes. At ~160 W
for 2h20 he oxidises roughly 63 g/h of carbohydrate, so absorbing 70–80 g/h of the 90
taken in leaves endogenous glycogen use near zero. What remains is fluid loss and thermal
strain, not depletion. Cutting the other way: durability is his named weakness, so he may
sit at the worse end.

### Bicarbonate is not the lever, and dew point is

Sodium bicarbonate buffers H+ from high glycolytic flux, so its benefit concentrates in
1–10 min efforts. Past 20 minutes it is roughly 0–1%, i.e. 0–3 W here. Against that: 90
g/h of carbohydrate goes in for 2h20 beforehand, and bicarb GI distress on top of that
load can cost 30 W. It has never been trialled in training, and the ride that sets the
FTP for the next four months is the wrong place to trial it.

**Dew point is about five times the lever bicarb is.** By the `plan.md` heat table a 70°F
dew point costs 4–6%, which puts 285 W out of reach on its own. Start early for the
coolest air available; that decision is worth more than every supplement and equipment
choice combined.

### Pacing

**Ride toward 285 W, don't hold it flat.** The climb rolls around a 4.4% average, so push
300–310 W on the steep pitches and let it sag to 265–270 W on the shallow sections — more
time is spent on the steep, so the variable pacing is worth 10–20 s for free.

Open at ~275 W for 3 min (the first minutes feel free; that is the trap), settled by
minute 5, empty it from minute 19.

**In-effort check at minute 10: if power is at 285 W and HR is below 172, he is
under-cooking it.** 25 Aug puts him at 152 bpm for 249 W, so there is a great deal of HR
between there and a max.

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
