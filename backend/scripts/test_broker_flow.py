"""Replicate the frontend Broker-page call sequence against a live server."""
from __future__ import annotations

import json
import sys
import time
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8091"


def j(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read() or "{}")


for _ in range(40):
    try:
        urllib.request.urlopen(BASE + "/health", timeout=2)
        break
    except Exception:
        time.sleep(0.5)

j("POST", "/demo/seed")
agents = j("GET", "/agents")
requester = next(a for a in agents if a["name"] == "ResearchAgent")
skill = "market-data"

# 1 discover
ranked = j("GET", f"/agents/search?skill={skill}")
provider = next(a for a in ranked if a["id"] != requester["id"])
print(f"1 discovery   -> {provider['name']} match={provider['match_score']}")

# 2 negotiate
offer = j("POST", "/offers/create", {"requester_id": requester["id"],
          "provider_id": provider["id"], "skill": skill, "amount": 10})
print(f"2 negotiation -> {offer['status']} @ ${offer['amount']}")
if offer["status"] == "countered":
    offer = j("POST", "/offers/accept", {"offer_id": offer["id"], "actor_id": requester["id"]})
    print(f"  accepted    -> @ ${offer['amount']}")

# 3 contract
c = j("POST", "/contracts/create", {"offer_id": offer["id"], "requester_id": requester["id"],
      "provider_id": provider["id"], "skill": skill, "amount": offer["amount"]})
j("POST", "/contracts/sign", {"contract_id": c["id"], "actor_id": requester["id"]})
signed = j("POST", "/contracts/sign", {"contract_id": c["id"], "actor_id": provider["id"]})
print(f"3 contract    -> {signed['status']}")

# 4 escrow
e = j("POST", "/escrow/create", {"contract_id": c["id"]})
print(f"4 escrow      -> {e['status']} locked ${e['amount']} fee ${e['fee']}")

# 5 delegate
t = j("POST", "/tasks/create", {"requester_id": requester["id"], "skill": skill,
      "contract_id": c["id"], "acceptance_criteria": {"type": "json",
      "schema": {"properties": {"value": {"type": "number"}}, "required": ["value"]}}})
j("POST", "/tasks/assign", {"task_id": t["id"], "assignee_id": provider["id"]})
j("POST", "/tasks/start", {"task_id": t["id"]})
j("POST", "/tasks/submit", {"task_id": t["id"], "result": {"data": {"value": 42}}})
print("5 delegation  -> submitted")

# 6 verify
v = j("POST", "/verify/task", {"task_id": t["id"]})
print(f"6 verification-> {v['verdict']} score={v['score']}")

# 7 settle
done = j("POST", "/tasks/complete", {"task_id": t["id"]})
print(f"7 settlement  -> {done['status']}")

# 8 audit
audit = j("GET", f"/audit/job/{c['id']}")
print(f"8 audit       -> {audit['count']} events: {[e['action'] for e in audit['events']]}")

assert signed["status"] == "signed"
assert e["status"] == "funded"
assert v["verdict"] == "passed"
assert done["status"] == "completed"
assert "escrow.released" in {ev["action"] for ev in audit["events"]}
print("\nBROKER FLOW OK - every UI endpoint integrated end to end")
