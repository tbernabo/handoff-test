# Results of external runs

Every run below was done by an agent that is not ours, against the production API at
forbiz.io. We publish what it found, including what it broke. A finding is listed with the
date it was measured, the API version at the time, and the version that fixed it, if any.
"Open" means open today. Nothing here is a claim we made about ourselves.

Where a finding says "verified by the third party", the same external agent re-ran the
check after the fix. Where it says "vendor PASS", only our own regression suite says it is
fixed, and that is a weaker statement.

---

## Run 5: the handoff test itself, first end-to-end run (2026-09-22, 02:32 UTC)

**Agent:** a Grok-based agent, run by an external tester. **Script:** `handoff_test.py` from this
repository, as published. **API:** 1.58.0.

| Session | Result | Detail |
|---|---|---|
| Session 1 (`--bootstrap`, record the commitment) | **exit 0** | Opened a trial workspace, recorded one commitment with `commitmentKey`, wrote the handoff file. |
| Session 2, check 1: recover the commitment by its key through search | **FAIL** | `GET /search?q=handoff-test/20260922-023214` answered 200 with **0 hits** in every collection. The action exists: `/export` of the same workspace lists it, with that exact `commitmentKey`. The full-text query was rewritten as `'handoff-test' <-> 'handoff' <-> 'test' <-> '/20260922-023214'`: the key was shattered on `/` and `-`, and nothing matched. |
| Session 2, checks 2 to 7 | **BLOCKED** | The script returns after check 1 fails; the other six never ran. |
| Session 2 overall | **exit 1** | |

**What it means.** A cold successor that holds only the commitment key cannot get past the first
step through search. The record does hold the key, and it does refuse a duplicate on it
(`POST /actions` with the same `commitmentKey` answers 409 `COMMITMENT_ALREADY_OPEN` with the
existing commitment inside), so the commitment is recoverable, but not through the door the
test uses and a successor would try first. **Open, Forbiz defect.** The tester's first change:
make `/search` find an exact `commitmentKey`, or stop the full-text parser from shattering keys
that contain `/` and `-`.

**Also measured in the same run, on the claimed workspace, read-only:** `trial.used.actions = 13`
(the fix of 1.58.0, confirmed by the third party); `/next` ranks the same four overdue
commitments that `/prompts` lists under `needs_feedback`, and differs only by one planned item
not yet due. The "nothing pending while overdue exist" finding of run 4 did not reproduce.

---

## Run 4: continuity across a claim, and the cold successor (2026-09-20 / 21)

**Agent:** a Grok-based agent, run by an external tester. **Brief:** [BENCHMARK.md](BENCHMARK.md),
blocks A to E. **API:** 1.56.0 at the start of the run, 1.58.0 at the end.

| Finding | Block | Severity | Status |
|---|---|---|---|
| **A credential bound to one workspace wrote into another workspace of the same owner.** The cold successor (C2) executed an action and recorded a signal on a commitment that belonged to a sibling workspace, with HTTP 200. Root cause: reads of `/prompts` and `/state` and the write gate filtered by user, not by workspace, and a claim puts two workspaces under one user. | C | Critical | **Fixed in 1.57.0** (2026-09-20). Verified by the third party on 2026-09-21: the same write now answers 409 `WRONG_WORKSPACE` and nothing of the other workspace leaks. The record written during the incident stays: signals are write-once by design. |
| **The trial counter reported the owner's total, not the workspace's.** A claimed workspace with 13 actions reported `used.actions = 45` and `remaining = 0`, while `POST /actions` still returned 201. Two defects: volume was counted by user (after a claim, that is every workspace the human owns), and a claimed workspace skipped enforcement while the announcement stayed on. | A8 | High | **Fixed in 1.58.0** (2026-09-21): volume is counted per workspace, and a claim lifts nothing about volume; only the plan does. Verified by the third party the same day, read-only: `/me` on the claimed workspace now reports `used.actions = 13`. |
| **`/next` says "nothing pending" while `/prompts` shows overdue items** in a real, claimed workspace; after recording a signal, `handoff.last_signal` still points to an earlier cycle. A cold successor that trusts `/next` stays idle on a business with overdue commitments. | C | High | **Open.** Hypothesis: `/next` only ranks what an agent can move and hides what waits for the human; if so, the defect is that it does not say so. |
| **`/state.signal_checks` lists ids of actions in practice projects.** Practice is excluded from queues but not from that block. | A4 | Low | **Open.** Known and out of scope by decision. |
| **A signal cannot be retracted.** A second `POST /signals` is 409; there is no `unexecute`. The tester first read this as a gap, then agreed it is the design: the record is append-only. What is missing is a vocabulary to annotate that an event was invalid or out of authority, so a successor reading history does not take the cross-workspace signal above as a real move. | C3 | Design question | **Open as a product hypothesis.** Today you can annotate without deleting (`interpret-signal` with a learning note, `close-loop`, evidence that `contradicts`), but none of those says "this event was invalid". |
| The trial credential survives the claim; `/me`, `/state`, `/next` and a small write keep working with the same key after the owner claims the workspace. | B1, B2 | | PASS, as designed since 1.32.0. |

**The C4 rating and the tester's full PASS/FAIL table are not reproduced here:** they live in
the tester's own dumps, not in our tree. What is above is what reached our defect record,
with its evidence.

**What this run taught about the product, beyond the bugs:** a well-intentioned external
agent, given a clear and narrow instruction, wrote outside its boundary without noticing and
without any signal. Containment cannot depend on the agent's discipline; for a few hours it did.

---

## Run 3: the landing and one full cycle, read by an agent (2026-09-19)

**Agent:** a Grok-based agent ("critiquito/1.0"). **API:** 1.54.0.

- It read `/llms.txt` first, then the API refusals, then the OpenAPI. The landing page was
  not its recipe. Fixes for agents belong in `/llms.txt` before the landing.
- `/next` empty while `/prompts` listed the action: explained by the `purpose: test` filter
  applied to some views and not others. **Fixed in 1.55.0.**
- `expectedSignalSource` was stored but echoed back as `null`, with the values in two
  other fields. **Fixed in 1.55.0.**
- Evidence: the natural word `observation` is not in the `kind` enum, and `/llms.txt` gave
  no example body. The 400 was good (it listed the enum); the documentation was not.
  **Fixed in 1.55.0.**
- Three contradictions inside one `/next` body after a signal was recorded: `signal_check.means`
  said no signal was recorded; `context.due_at` was the review clock, not the action's
  deadline; `lifecycle_status` said `waiting_for_signal` while the temporal state said
  `needs_decision`. **Fixed in 1.55.0.**
- `purpose` on an action was accepted and did nothing, while `/llms.txt` implied it hid the
  action. **Fixed in 1.56.0:** the response now says `purpose_ignored` and where practice
  belongs (a project).

---

## Run 2: the claim in production (2026-09-10)

**Agent:** a Grok-based agent. Verified in production that claiming a workspace no longer
revokes the agent's credential, which was the critical finding of run 1. **Fixed in 1.32.0.**

---

## Run 1: the journey from zero (2026-09-06 / 07)

**Agent:** a ChatGPT agent, session with no context. **API:** 1.25.0.

- **Blind, it did not find Forbiz.** Asked for "a system of record to run a business with
  agents", it picked a competitor. Given the name, it chose Forbiz **for the contract**
  (bootstrap without an account, documented refusals). Finding: the first link of the
  journey had no surface; forbiz.io spoke only to humans. `/llms.txt` and `/openapi.json`
  at the root exist since then.
- Bootstrap PASS; the provisional workspace expired after twelve hours of inactivity and
  no human was nudged. Trials end by volume, not by clock, since 1.27.0.
- **The claim revoked the agent's credential in the same instant**, leaving no route to a
  new one: continuity was cut exactly when the owner took the workspace. Critical.
  **Fixed in 1.32.0**, verified in run 2.
- Eight smaller contract defects (root of the API answered 401 without saying how to
  enter; a search parameter ignored silently; an epistemic status normalised without
  warning; two routes for the same object with different contracts; and others). Most
  fixed between 1.26.0 and 1.36.0; the details are in our internal defect record.

---

## How to add a run

Run [BENCHMARK.md](BENCHMARK.md) or `handoff_test.py` against your own provisional workspace,
keep the bodies, and open an issue or a pull request with the table. We publish failures.
