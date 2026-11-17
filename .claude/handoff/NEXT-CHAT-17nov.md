# Hand-over to the next chat (17 Nov 2026, written by the main session)

**UPDATE 10:15, 17 Nov: steps 1-2 below are DONE.** The post-fix run passed (API 611 with the real worker, e2e 110,
harness 27, mock arm); the batch is committed (b7a7cb1) and `main` is fast-forwarded to it; the working tree is on
`main`, clean. The owner was told to restart the app. **Start at step 4** (the door finder's round), unless they ask
for something else.

The owner (panachai.t; "James" in Claude Docs; use they/them) is moving to a new chat. Read this first; do not make
them explain again. Their standing rules are in `~/.claude/CLAUDE.md` (never deploy) and the memory notes (loaded
automatically): above all **build the queued work first with quick targeted checks, then test the whole batch ONCE
and review it once** (walkthrough-batch-then-test), never write `app/data`, never use ports 5710 / 8710 (their running
`npm run dev`, which serves this working tree live), plain short answers, a status line every 10-15 min during long runs.

## Where things stand

- Project: `C:\Users\DWP2\Desktop\Project walkthrough`, app in `app/`. Owner's summary: `app/docs/STATUS.md`.
- `main` = 52a03f2 (jump, chairs, UP on any layer, delete project / version / draft). Local git only, never pushed.
- Branch **`box-delete`** (checked out) holds the **16-17 Nov batch**, not yet on main:
  1. the hotel's stair climbs (`packages/viewer/src/model/upgrade.ts`: an older model's complete flight of step blocks
     becomes climbable in memory; only the hotel qualifies; its walk-parity entry re-recorded on purpose);
  2. the bank's narrow north stair climbs (`services/builder/.../build/network.py`: a mostly-stair unfloored strip is
     floored when closed off, flagged when not; the bank's new-rule pins moved, `BANK_NEW_RULE_SHA1` a36e1535...);
  3. **delete one furniture box** (design `app/docs/boxes/DESIGN.md`, record `app/docs/contract-issues/BX.md`).
- Commits on the branch: 0eff212 (design), fb0ca8e, 7190417, df6b92c (merge), 700d809 (batch + one full check: unit
  1181, API 607 also with the real worker, builder, acceptance rooms steps, the eight old versions as on 9 Nov, e2e 404,
  harness 76). Then a review round (two reviewers) and its fixes, **uncommitted in the working tree**:
  - server/web: carry-over pairs floors by level + stack (never by floor key), kind dropped from the match, the
    not-carried note names each box (additive API field `CarriedEdits.boxes`), the draft preview line, "Give it a
    kind" scrolls, a re-created viewer syncs to the saver (`settled()`);
  - viewer: Walk double-Delete guard, "(Del)" only when armed, restored box under an upper floor shows no marker;
  - `tests/e2e/leak.spec.ts` (shows the box's floor first), docs: STATUS.md (section "Added on 16-17 Nov"), the plan
    (hours: box editing row 38 h; totals ~818 / 1,023 / 1,453 h; next action 18), `app/docs/boxes/DESIGN.md` 5.1 note,
    BX.md sections. Product doc (Claude Docs) already updated to rev 98.
- Post-fix test run (`bash %TEMP%\wt-bc\fixrun.sh`, summary `%TEMP%\wt-bc\logs\fixrun-summary.txt`): fresh template,
  e2e box-delete / furniture / web / deletes / leak / web-leak / offline **110 passed**, harness and the mock arm passed;
  the API run with `WT_INTEGRATION=1` was the last step (check its line in the summary: expect 611+ passed).

## What to do next, in order

1. If the summary has no `fx-api-int exit 0` line, run only that step again (alone; see the script's last `step`).
2. Commit the working tree on `box-delete` (leave out `app/data/`, `.claude/`, `app/docs/.claude/`), then
   `git fetch -q . box-delete:main` (fast-forward main). Check STATUS.md's "Checked once" bullet against the real counts.
3. Tell the owner: restart the app (Ctrl+C, then `npm run dev`), reload; what to try (hotel: hold W up the stair;
   TEST_BANK: New version → Use the files of v1 again → Build → Save, both stairs climb; Orbit click a box → Delete,
   Ctrl+Z, the Restore list). Nothing to deploy.
4. Then the next item on their list: **the door finder's second fix round** (plan next action 16). Design it once first
   (it is a milestone), with the owner's decisions K and L of 12 Nov (a terrace's name stays its label; a room fix
   remembers its room), FID-2 (door swings on the window layer), the Revit suite's armchair closings, the north stair's
   top on Level 2 (a closed pocket with no door: a missed door?), and a flag for a door symbol that got no opening.

## Known leftovers (told to the owner)

- The north stair is reached by double-clicking its steps (its top pocket has no door).
- The filtered 3ds Max script (deleted boxes left out) has not been run in real 3ds Max: ask the 3D team.
- Hotel: Ghost → Walk from just above Floor 2 can land on Floor 1 (the climbing walker's rule, as for every new model).
