# The continuity benchmark

`handoff_test.py` measures the smallest case: one commitment, two processes, seven checks.
This document is the larger test we hand to an external agent. It measures what happens
**after** the first cycle: when the owner claims the workspace, when the same agent comes
back cold, and when a different agent inherits the work.

It is written as a brief you can paste into any agent that can call an HTTP API. Nothing in
it needs an account, an email or a human: `POST /bootstrap` opens a trial workspace.
Read [forbiz.io/llms.txt](https://forbiz.io/llms.txt) first; the contract changes often and
that file is the one that is kept current.

Scope rule for anyone running it: **only your own provisional workspaces.** Never a
workspace you did not create, never email, never outreach, never money.

---

## The brief

```
Test brief for Forbiz. Read /llms.txt first. Keep the agent key out of
everything you send back.

Scope limit: your own provisional workspaces only. Open one with
POST /bootstrap (two if block C needs a clean one). Never touch any other
workspace.

For every check below, save the full request and response bodies with UTC
timestamps, and say PASS / FAIL / BLOCKED plus what you expected.

A. THE CONTRACT - verify or refute what the documentation says
A1. POST /actions with {"purpose":"test"}: the response should carry
    purpose_ignored true and a note saying purpose is a project field, and
    the action SHOULD still appear in /prompts and /state. That is the
    truthful behaviour, not a bug.
A2. POST /actions without purpose: no purpose_ignored field at all.
A3. An action inside a project with purpose test: absent from /next,
    /state queues, /prompts and /decisions/recommendation.
A4. /state signal_checks: does it list ids of actions that live in a
    practice project? Confirm or refute, with the ids.
A5. COMMITMENT_ALREADY_OPEN with confirm_new true: still 409, body carries
    existing + commands. /llms.txt should mention confirm_new only next to
    POSSIBLE_DUPLICATE.
A6. After a signal is recorded: no response anywhere should say
    lifecycle_status "waiting_for_signal" for that action; /next
    signal_check.means should not say "No signal was recorded"; /next
    context.due_at should equal the action's own due_at (not the review
    clock). Send the /next body.
A7. Create an action with expectedSignalSource {kind, detail}: the response
    should carry expected_signal_source_declared with both values.
A8. Trial volume: read trial.used and trial.remaining on /me. Past the
    limit, POST /actions must answer 403 PROVISIONAL_TRIAL_COMPLETE with
    unlocks_with, and used must count THIS workspace only.

B. CONTINUITY ACROSS THE CLAIM - the part nobody tests twice
Have the owner claim the workspace (POST /claim-link gives the link).
B1. With the SAME credential you used before the claim: read /me, /state,
    /next. Do they still work? Say exactly what changed in /me (plan,
    limits, authority, workspace type).
B2. Write something small there (one evidence item). Does it still work, or
    is there a new refusal? Quote the refusal.
B3. Does anything tell you the workspace now has a human owner, or that your
    access could be rotated? If nothing says so, that is the finding.

C. THE COLD SUCCESSOR - the core claim
Start a session with NO memory of the earlier work: pretend you are a
different agent that just received this credential and nothing else.
C1. Using only the API, answer in writing: what is this business, what is
    open right now, what was already decided and must not be re-litigated,
    and what is the single next move. Say which endpoints gave you each
    answer.
C2. Now do that next move: execute, record a signal, interpret, close the
    loop or create the child action.
C3. Then say plainly: what did you have to guess? What would a human have
    had to tell you that the API did not? Quote the field or endpoint that
    should have carried it.
C4. Rate the handoff 1-5 and say what one change would raise it most.

D. THE REFUSALS - are they actionable?
Trigger at least four refusals on purpose (bad enum, missing scope, trial
limit if you can reach it, an authority you do not have). For each: does
the body say what to send instead, or only what is wrong? A refusal that
does not carry the next move is a finding.

E. WHAT YOU WOULD NOT DO
Name anything in this API you would refuse to do on a real business without
a human confirming first, and say why. We want the list, not reassurance.

Do NOT: send email, touch outreach on a real workspace, claim or rotate
anything yourself, or create more provisional workspaces than you need.

Report: the table of checks with PASS/FAIL/BLOCKED, the bodies, and your
three most expensive findings in order, with the change you would make.
```

---

## How to read a result

- **A** verifies the published contract. A FAIL here is a Forbiz bug, and it goes into the
  public record the same day.
- **B** is the only block where a FAIL is critical: if the credential dies with the claim,
  the product loses exactly what it promises.
- **C** has no PASS or FAIL. It is material: what the agent had to guess is the list of
  what the contract still lacks, and it comes from a third party, not from us.
- **D** and **E** are cheap, and they produced the best findings so far: actionable
  refusals are what the first external agent praised.

## What has been run

See [RESULTS.md](RESULTS.md) for every external run, what it found, what was fixed and in
which version, and what is still open. Failures are published as found.
