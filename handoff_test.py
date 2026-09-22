#!/usr/bin/env python3
"""
The handoff test.

Can a fresh AI agent, with no conversation history, recover a commitment
another agent recorded, explain its current state, and identify the next
justified step, without duplicating it and without inventing an outcome?

This script runs that test against a Forbiz workspace in two independent
processes ("sessions"), so that nothing but the durable record and an
authorized credential connects them.

  session 1  records one commitment with an expected signal, its source and a
             deadline, checks the source once, and writes a tiny handoff file
             that holds ONLY the commitment key (no ids, no credential, no
             history).
  session 2  starts from that key alone and must recover the commitment,
             its state, what was already checked, and the next step. It also
             tries to open the same commitment again: the record must refuse.

Standard library only. Python 3.9+.

Usage
  export FORBIZ_CREDENTIAL=...      # agent credential for the workspace
  python handoff_test.py session1   # record the commitment
  python handoff_test.py session2   # recover it from a clean process

  Without FORBIZ_CREDENTIAL, session1 can bootstrap a trial workspace:
  python handoff_test.py session1 --bootstrap
  It prints the credential once; export it before running session2.

Exit code 0 when every check passes, 1 otherwise. Nothing here sends email,
messages or money: a trial credential cannot, and this script never asks to.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone

API = os.environ.get("FORBIZ_API", "https://forbiz.io/api/public/agent")
USER_AGENT = "handoff-test/1.1"
HANDOFF_FILE = os.environ.get("HANDOFF_FILE", "handoff.json")


# ---------------------------------------------------------------- transport

def call(method, path, body=None, credential=None, idempotent=True):
    """One HTTP call. Returns (status, parsed_json_or_text)."""
    url = API + path
    data = None
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if credential:
        headers["Authorization"] = "Bearer " + credential
    if method in ("POST", "PATCH") and idempotent:
        headers["Idempotency-Key"] = str(uuid.uuid4())
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            status = resp.status
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        status = e.code
    try:
        return status, json.loads(raw)
    except ValueError:
        return status, raw


def credential_from_env():
    cred = os.environ.get("FORBIZ_CREDENTIAL")
    if not cred:
        sys.exit("FORBIZ_CREDENTIAL is not set. Run session1 --bootstrap first, "
                 "or export a credential for an existing workspace.")
    return cred


# ---------------------------------------------------------------- checks

class Report:
    def __init__(self):
        self.rows = []

    def check(self, name, ok, detail=""):
        self.rows.append((name, bool(ok), detail))
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {name}" + (f"  ({detail})" if detail else ""))
        return ok

    def passed(self):
        return all(ok for _, ok, _ in self.rows)


# ---------------------------------------------------------------- session 1

def session1(args):
    print("session 1: record one commitment")
    cred = os.environ.get("FORBIZ_CREDENTIAL")
    if args.bootstrap and not cred:
        status, out = call("POST", "/bootstrap", {
            "agent_name": "handoff-test-session-1",
            "client_name": "handoff-test",
            "client_version": "1.0",
            "source": "handoff-test",
        })
        if status != 201:
            sys.exit(f"bootstrap failed: {status} {out}")
        cred = (out.get("credential") or {}).get("api_key")
        if not cred:
            sys.exit(f"bootstrap answered 201 without credential.api_key: {json.dumps(out)[:300]}")
        print("  trial workspace created. Export this before session 2 "
              "(shown once, not stored by this script):")
        print(f"  export FORBIZ_CREDENTIAL={cred}")
        claim = out.get("claim") or {}
        if claim.get("claim_url"):
            print(f"  claim url for a human owner: {claim['claim_url']}")
    if not cred:
        cred = credential_from_env()

    key = args.key or f"handoff-test/{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    friday = next_weekday(4).replace(hour=17, minute=0, second=0, microsecond=0)

    body = {
        "description": "Follow up on the revised proposal",
        "verb": "send",
        "whyThisMove": "Customer asked for a revised proposal on Thursday; discount approved.",
        "expectedSignal": "Customer accepts or requests changes",
        "expectedSignalSource": {"kind": "email_thread", "detail": "Email thread 'Revised proposal'"},
        "expectedSignalAt": iso(friday),
        "dueAt": iso(friday),
        "commitmentKey": key,
        "roi": {"cash": 3, "access": 1, "proof": 2, "narrative": 1,
                "relationship": 3, "learning": 1, "compliance": 0},
    }
    status, out = call("POST", "/actions", body, cred)
    if status != 201:
        sys.exit(f"could not record the commitment: {status} {json.dumps(out)[:400]}")
    action_id = out.get("action_id") or (out.get("action") or {}).get("id")
    print(f"  recorded action {action_id} with commitmentKey {key}")

    # one honest check of the declared source: nothing there yet.
    now = datetime.now(timezone.utc)
    status, chk = call("POST", f"/actions/{action_id}/signal-checks", {
        "source": {"kind": "email_thread", "detail": "Email thread 'Revised proposal'"},
        "period": {"from": iso(now - timedelta(days=1)), "to": iso(now)},
        "looked_for": "acceptance or a request for changes",
        "result": "not_found_in_source",
        "note": "handoff test, session 1",
    }, cred)
    if status != 201:
        print(f"  warning: signal-check not recorded: {status} {json.dumps(chk)[:300]}")
    else:
        print(f"  signal check recorded: {chk.get('means', '')}")

    with open(HANDOFF_FILE, "w", encoding="utf-8") as f:
        json.dump({"commitmentKey": key}, f)
    print(f"  handoff file written: {HANDOFF_FILE} (holds only the commitment key)")
    print("  session 1 done. Start session 2 from a clean process.")


# ---------------------------------------------------------------- session 2

def session2(args):
    print("session 2: recover the commitment from the key alone")
    cred = credential_from_env()
    with open(HANDOFF_FILE, encoding="utf-8") as f:
        key = json.load(f)["commitmentKey"]
    r = Report()

    # 1. recover the same commitment by its key, through the record's own
    #    mechanism: a commitment key is unique, so asking to open it again is
    #    refused, and the refusal hands back the existing commitment. The key is
    #    NOT a search term (the first published version of this check assumed it
    #    was, and failed against 1.58.0; see RESULTS.md, run 5).
    status, dup = call("POST", "/actions", {
        "description": "Follow up on the revised proposal",
        "commitmentKey": key,
        "expectedSignal": "Customer accepts or requests changes",
    }, cred)
    code = dup.get("code") if isinstance(dup, dict) else None
    existing = dup.get("existing") if isinstance(dup, dict) else None
    action_id = (existing or {}).get("id") if isinstance(existing, dict) else None
    r.check("recovered the commitment by its key (409 returned the existing one)",
            status == 409 and code == "COMMITMENT_ALREADY_OPEN" and bool(action_id),
            f"{status} {code or ''} existing={action_id or 'none'}".strip())
    if not action_id:
        print(json.dumps(dup)[:600])
        return finish(r)

    # 2. current state, from the record
    status, one = call("GET", f"/actions/{action_id}", credential=cred)
    action = one.get("action", {}) if isinstance(one, dict) else {}
    state = action.get("lifecycle_status") or action.get("status")
    r.check("read its current state", status == 200 and state, f"state={state}")
    expected = action.get("expected_signal")
    by = action.get("expected_signal_at") or (action.get("timing") or {}).get("due_at")
    r.check("expected signal and deadline survived", expected and by,
            f"expects '{expected}' by {by}")

    # 3. what was already checked, with scope: never "the customer did not answer"
    status, checks = call("GET", f"/actions/{action_id}/signal-checks", credential=cred)
    n = checks.get("count", 0) if isinstance(checks, dict) else 0
    means = [c.get("means", "") for c in (checks.get("checks", []) if isinstance(checks, dict) else [])]
    r.check("knows what was already checked, and where", status == 200 and n >= 1,
            (means[-1] if means else "no checks on record"))

    # 4. the next justified step, from the record's own ranking
    status, nxt = call("GET", "/next", credential=cred)
    handoff = nxt.get("handoff") if isinstance(nxt, dict) else None
    r.check("has a next step with a handoff for a successor", status == 200 and (handoff or nxt.get("message")),
            (json.dumps(handoff)[:160] if handoff else nxt.get("message", "")))

    # 5. the refusal in check 1 is not a dead end: it carries the commands to
    #    continue the existing commitment, executable as they came back
    commands = dup.get("commands") if isinstance(dup, dict) else None
    n_cmd = len(commands) if isinstance(commands, (list, dict)) else 0
    r.check("the refusal carried commands to continue the existing commitment", n_cmd >= 1,
            f"{n_cmd} command(s) in the 409 body")

    # 6. no invented outcome: the record holds no actual signal and no outcome
    r.check("no outcome was invented",
            not action.get("actual_signal") and not action.get("outcome_status"),
            f"actual_signal={action.get('actual_signal')!r} outcome_status={action.get('outcome_status')!r}")

    return finish(r)


# ---------------------------------------------------------------- helpers

def finish(r):
    print("\nresult:", "PASS" if r.passed() else "FAIL",
          f"({sum(1 for _, ok, _ in r.rows if ok)}/{len(r.rows)} checks)")
    sys.exit(0 if r.passed() else 1)


def collect_actions(search_result):
    """Pull action-like hits out of the search response, whatever its shape."""
    if not isinstance(search_result, dict):
        return []
    results = search_result.get("results")
    if isinstance(results, dict):
        acts = results.get("actions")
        if isinstance(acts, list):
            return acts
        if isinstance(acts, dict) and isinstance(acts.get("items"), list):
            return acts["items"]
    if isinstance(results, list):
        return [x for x in results if isinstance(x, dict)]
    if isinstance(search_result.get("actions"), list):
        return search_result["actions"]
    return []


def urlquote(s):
    from urllib.parse import quote
    return quote(s, safe="")


def iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def next_weekday(weekday):
    now = datetime.now(timezone.utc)
    days = (weekday - now.weekday()) % 7 or 7
    return now + timedelta(days=days)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("session", choices=["session1", "session2"])
    p.add_argument("--bootstrap", action="store_true", help="session1 only: create a trial workspace if no credential is set")
    p.add_argument("--key", help="session1 only: commitment key to use (default: timestamped)")
    args = p.parse_args()
    (session1 if args.session == "session1" else session2)(args)


if __name__ == "__main__":
    main()
