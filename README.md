# The handoff test

Your next AI agent should inherit your business, including its unfinished promises.

This repository holds two things:

1. **`handoff_test.py`**: a small, runnable test of that claim. Two processes, one
   commitment, seven checks.
2. **[BENCHMARK.md](BENCHMARK.md)**: the larger brief we hand to external agents, covering
   what happens after the first cycle: the owner claims the workspace, the agent comes back
   cold, a different agent inherits the work. **[RESULTS.md](RESULTS.md)** lists every
   external run so far, what it found, what was fixed and in which version, and what is
   still open. We publish failures as found.

## The small test

It asks one question:

> Can a fresh agent, with no conversation history, recover a commitment another agent
> recorded, explain its current state, and identify the next justified step,
> without duplicating it and without inventing an outcome?

It runs as two independent processes, so nothing but the durable record and an
authorized credential connects them. Session 1 records one commitment with an
expected signal, its source and a deadline, checks the source once, and writes a
handoff file that holds only the commitment key. Session 2 starts from that key
and has to recover everything else.

### What session 2 must show

| # | Check | Why it matters |
|---|---|---|
| 1 | Recovers the commitment by its key, through search, not by a stored id | A successor never has the id |
| 2 | Reads its current state from the record | Not from a summary someone wrote |
| 3 | The expected signal and deadline survived | Continuity is about what was promised |
| 4 | Knows what was already checked, and where | "Checked one email thread through Friday" is not "the customer did not reply" |
| 5 | Gets a next step with a handoff for a successor | The record ranks, the agent does not guess |
| 6 | Is refused when it opens the same commitment again | No duplicates, enforced by the record |
| 7 | No outcome was invented | The record holds no actual signal and no outcome |

Exit code 0 when every check passes.

### Run it against Forbiz

Standard library only, Python 3.9 or newer.

```bash
export FORBIZ_CREDENTIAL=...        # agent credential for a workspace
python handoff_test.py session1
python handoff_test.py session2     # from a clean process
```

No credential yet? Session 1 can open a trial workspace with no account, no email
and no human, then prints the credential once:

```bash
python handoff_test.py session1 --bootstrap
```

A trial credential cannot send email, messages or money, and this script never asks
to. Trial limits and plans are described in
[forbiz.io/llms.txt](https://forbiz.io/llms.txt); the API is documented at
[forbiz.io/openapi.json](https://forbiz.io/openapi.json).

**Status of the script:** request and response shapes were checked against the OpenAPI
3.1 document served at version 1.58.0. External runs, with their exit codes, are listed in
[RESULTS.md](RESULTS.md).

### Run it against anything else

The checks are the point, not the endpoint. If your business memory lives
somewhere else, port the seven checks. The hard ones are 4 and 6: most systems
can store a note, few can say what was checked over which period, and fewer
refuse a duplicate on their own.

## The larger benchmark

[BENCHMARK.md](BENCHMARK.md) is a brief for any agent that can call an HTTP API. It needs no
account. It measures the contract (A), continuity across the owner's claim (B), a cold
successor doing the next move with nothing but the credential (C), whether refusals carry
the next step (D), and what the agent would refuse to do without a human (E).

It has been run four times by external agents. The first run, blind, did not find Forbiz at
all. The fourth found that a credential could write into a sibling workspace of the same
owner, which was fixed the same day. All of it is in [RESULTS.md](RESULTS.md).

## Why this test exists

A transcript can tell you what people discussed. To continue the work, an agent also
needs what remains committed, who is responsible, what was expected to happen and by
when, where the evidence should appear, what was actually observed, and which decision
is still missing. The longer argument is in
[CRM for AI Agents: Your Business Should Outlive the Chat](https://forbiz.io/?utm_source=github&utm_medium=readme&utm_campaign=handoff_test).

Built by [Forbiz](https://forbiz.io/?utm_source=github&utm_medium=readme&utm_campaign=handoff_test).
MIT licensed: copy the checks.
