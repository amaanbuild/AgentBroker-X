"""Hit every API endpoint in dependency order and report PASS/FAIL for each."""
from __future__ import annotations

import sys
import time
import urllib.request
import urllib.error
import json

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8090"
results: list[tuple[str, int, bool, str]] = []


def call(method: str, path: str, body: dict | None = None, expect=(200, 201)):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            payload = json.loads(r.read() or "{}")
            ok = r.status in expect
            results.append((f"{method} {path}", r.status, ok, ""))
            return payload
    except urllib.error.HTTPError as e:
        ok = e.code in expect
        results.append((f"{method} {path}", e.code, ok, e.read().decode()[:80]))
        return {}
    except Exception as e:  # noqa: BLE001
        results.append((f"{method} {path}", 0, False, str(e)[:80]))
        return {}


# Wait for server.
for _ in range(40):
    try:
        urllib.request.urlopen(BASE + "/health", timeout=2)
        break
    except Exception:
        time.sleep(0.5)

# --- Meta ---
call("GET", "/")
call("GET", "/health")

# --- Registry ---
buyer = call("POST", "/agents/register", {"name": "SmokeBuyer", "skills": ["research"], "price_per_task": 60})
seller = call("POST", "/agents/register", {"name": "SmokeSeller", "skills": ["market-data"], "price_per_task": 20})
B, S = buyer.get("id"), seller.get("id")
call("GET", "/agents")
call("GET", "/agents/search?skill=market-data")
call("GET", f"/agents/{S}")

# --- Reputation ---
call("GET", f"/reputation/{S}")
call("POST", "/reputation/rate", {"agent_id": S, "rating": 5})

# --- Negotiation (create/counter/accept on one, reject on another) ---
offer = call("POST", "/offers/create", {"requester_id": B, "provider_id": S, "skill": "market-data", "amount": 10})
O = offer.get("id")
call("GET", f"/offers/{O}")
call("POST", "/offers/counter", {"offer_id": O, "actor_id": B, "amount": 18})
call("POST", "/offers/accept", {"offer_id": O, "actor_id": B})
offer2 = call("POST", "/offers/create", {"requester_id": B, "provider_id": S, "skill": "market-data", "amount": 5})
call("POST", "/offers/reject", {"offer_id": offer2.get("id"), "actor_id": B})

# --- Contract ---
contract = call("POST", "/contracts/create", {"offer_id": O, "requester_id": B, "provider_id": S, "skill": "market-data", "amount": 20})
C = contract.get("id")
call("POST", "/contracts/sign", {"contract_id": C, "actor_id": B})
call("POST", "/contracts/sign", {"contract_id": C, "actor_id": S})
call("GET", f"/contracts/{C}")

# --- Escrow ---
escrow = call("POST", "/escrow/create", {"contract_id": C})
E = escrow.get("id")
call("GET", f"/escrow/{E}")

# --- Task lifecycle ---
task = call("POST", "/tasks/create", {
    "requester_id": B, "skill": "market-data", "contract_id": C,
    "acceptance_criteria": {"type": "json", "schema": {"properties": {"value": {"type": "number"}}, "required": ["value"]}}})
T = task.get("id")
call("POST", "/tasks/assign", {"task_id": T, "assignee_id": S})
call("POST", "/tasks/start", {"task_id": T})
call("POST", "/tasks/submit", {"task_id": T, "result": {"data": {"value": 42}}})
call("GET", f"/tasks/{T}")
# verify standalone before completing
call("POST", "/verify/task", {"task_id": T})
call("POST", "/tasks/complete", {"task_id": T})
call("POST", "/escrow/release", {"escrow_id": E}, expect=(200, 201, 409))  # already released

# --- Refund path on a fresh escrow ---
c2 = call("POST", "/contracts/create", {"requester_id": B, "provider_id": S, "skill": "market-data", "amount": 15})
call("POST", "/contracts/sign", {"contract_id": c2.get("id"), "actor_id": B})
call("POST", "/contracts/sign", {"contract_id": c2.get("id"), "actor_id": S})
e2 = call("POST", "/escrow/create", {"contract_id": c2.get("id")})
call("POST", "/escrow/refund", {"escrow_id": e2.get("id")})

# --- Supervisor ---
call("GET", "/jobs/active")
call("POST", "/jobs/sweep")
# reassign needs an assigned task
rt = call("POST", "/tasks/create", {"requester_id": B, "skill": "market-data"})
call("POST", "/tasks/assign", {"task_id": rt.get("id"), "assignee_id": S})
call("POST", "/jobs/reassign", {"task_id": rt.get("id"), "reason": "manual"})

# --- Audit ---
call("GET", f"/audit/job/{C}")
call("GET", f"/audit/agent/{S}")

# --- SkillMD ---
call("POST", "/skillmd/generate", {"name": "X", "skills": ["y"], "endpoint": "https://x"})
call("POST", "/skillmd/generate", {"agent_id": S})

# --- Demo ---
call("POST", "/demo/seed")
call("POST", "/demo/run")

# --- Report ---
passed = sum(1 for _, _, ok, _ in results if ok)
print(f"\n{'ENDPOINT':40} STATUS  RESULT")
print("-" * 70)
for name, status, ok, err in results:
    mark = "PASS" if ok else "FAIL"
    line = f"{name:40} {status:<6}  {mark}"
    if not ok:
        line += f"  <- {err}"
    print(line)
print("-" * 70)
print(f"{passed}/{len(results)} endpoints passed")
sys.exit(0 if passed == len(results) else 1)
