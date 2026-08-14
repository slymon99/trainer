---
name: adjust-plan
description: Revise the overall training plan in plan.md — change the block structure, targets, zones, weekly layout or decision rules, or re-anchor FTP. Use when asked to update the training plan, change the goal or timeline, re-anchor FTP/threshold, restructure a block, or adapt the plan after illness, travel, or a missed period of training.
---

# Adjust the training plan

The plan lives in `plan.md` at the repo root, with the parts that have a different
lifecycle split into `plan/`:

| File | What it holds | Read it when |
|---|---|---|
| `plan.md` | The standing brief — athlete, zones, the week, decision rules | **Always** |
| `plan/block-1.md` (etc.) | The current block's weeks, trips, test date | Planning or reviewing a week |
| `plan/roadmap.md` | Later blocks, CTL targets, the test schedule | Changing block structure or timeline |
| `plan/decisions.md` | Re-anchor history, past corrections and why | Re-anchoring, or when a rule looks wrong |
| `plan/check-ins.md` | Weekly subjective check-in answers | Running the check-in |

It's free-form: read it and work with the structure the athlete already chose. Don't
impose a template on it.

If `plan.md` doesn't exist yet, offer to draft one by interviewing the user. Don't
invent an athlete profile to fill gaps.

## Before changing anything

1. **Read `plan.md` in full**, plus whichever `plan/` files the change touches. The
   files cross-reference each other — a change to zones usually implies changes to
   the week layout and the progression rules.
2. If the plan carries its own instructions for whoever plans from it, those win
   over anything in this skill.
3. Run the `review-training` skill first when the adjustment is driven by how
   training has actually been going. Change the plan from data, not vibes.

## Rules for editing

- **Keep targets as percentages of FTP, never absolute watts.** The plan is written
  that way deliberately: intervals.icu resolves `%` against sport settings, so
  re-anchoring updates every scheduled workout at once. Writing a watt number into
  the plan or a workout creates a figure that goes stale silently — which is the
  documented root cause of the athlete's 2026 plateau.
- **Change the working FTP only through the plan's own re-anchoring protocol**, and
  say so explicitly when you do. A block feeling easy is not sufficient reason —
  that's the specific failure mode such a protocol exists to prevent. Record it in
  `plan/decisions.md`.
- **Prefer deleting a rule to adding one that qualifies it.** This plan has already
  been through one round of accretion where dated amendments, reconciliations and
  scope notes grew to outweigh the rules themselves and started contradicting them.
  If a rule needs a caveat to survive contact with a real week, the rule is probably
  wrong. Put the reasoning in `plan/decisions.md`, not inline.
- **Don't write a rule that runs on RPE alone.** It resolves to about ±1, which
  isn't enough precision to change a week of training on.
- **Update the plan's assumptions section** whenever one is confirmed or refuted.
- When the underlying diagnosis changes, say plainly what new evidence changed it.
  A plan whose rationale silently mutates can't be evaluated later.
- Keep it internally consistent: if weekly hours drop, the load arithmetic and the
  block roadmap must both be redone, not just the week table.

## After editing

Summarize as a diff in prose: what changed, why, and what it implies for the next
week of training. Ask whether to push the revised week to the calendar with the
`create-workouts` skill.
