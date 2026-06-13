"""End-to-end economy flow: negotiate → contract → escrow → task → verify → pay."""


def test_full_lifecycle(client, two_agents):
    buyer, seller = two_agents

    # 1. Negotiate - buyer offers below seller's reservation (20) → counter.
    offer = client.post("/offers/create", json={
        "requester_id": buyer["id"], "provider_id": seller["id"],
        "skill": "market-data", "amount": 10}).json()
    assert offer["status"] in {"countered", "accepted"}

    # Buyer accepts whatever the negotiation converged to.
    client.post("/offers/accept", json={
        "offer_id": offer["id"], "actor_id": buyer["id"]})

    # 2. Contract - create + dual-sign.
    contract = client.post("/contracts/create", json={
        "offer_id": offer["id"], "requester_id": buyer["id"],
        "provider_id": seller["id"], "skill": "market-data",
        "amount": offer["amount"]}).json()
    client.post("/contracts/sign", json={
        "contract_id": contract["id"], "actor_id": buyer["id"]})
    signed = client.post("/contracts/sign", json={
        "contract_id": contract["id"], "actor_id": seller["id"]}).json()
    assert signed["status"] == "signed"

    # 3. Escrow - funds locked.
    escrow = client.post("/escrow/create", json={
        "contract_id": contract["id"]}).json()
    assert escrow["status"] == "funded"

    buyer_after = client.get(f"/agents/{buyer['id']}").json()
    assert buyer_after["balance"] == 1000.0 - escrow["amount"]

    # 4. Task - create, assign, start, submit.
    task = client.post("/tasks/create", json={
        "requester_id": buyer["id"], "skill": "market-data",
        "contract_id": contract["id"],
        "acceptance_criteria": {
            "type": "json",
            "schema": {"properties": {"value": {"type": "number"}},
                       "required": ["value"]}}}).json()
    client.post("/tasks/assign", json={
        "task_id": task["id"], "assignee_id": seller["id"]})
    client.post("/tasks/start", json={"task_id": task["id"]})
    client.post("/tasks/submit", json={
        "task_id": task["id"], "result": {"data": {"value": 42}}})

    # 5. Complete - verify passes, escrow releases, reputation rises.
    done = client.post("/tasks/complete", json={"task_id": task["id"]}).json()
    assert done["status"] == "completed"

    escrow_after = client.get(f"/escrow/{escrow['id']}").json()
    assert escrow_after["status"] == "released"

    seller_after = client.get(f"/agents/{seller['id']}").json()
    payout = escrow["amount"] - escrow["fee"]
    assert seller_after["balance"] == 1000.0 + payout
    assert seller_after["successful_jobs"] >= 1

    # 6. Audit - the whole job is traceable.
    audit = client.get(f"/audit/job/{contract['id']}").json()
    assert audit["count"] > 0
    actions = {e["action"] for e in audit["events"]}
    assert "escrow.released" in actions


def test_verification_failure_refunds(client, two_agents):
    buyer, seller = two_agents
    contract = client.post("/contracts/create", json={
        "requester_id": buyer["id"], "provider_id": seller["id"],
        "skill": "market-data", "amount": 30}).json()
    client.post("/contracts/sign", json={"contract_id": contract["id"], "actor_id": buyer["id"]})
    client.post("/contracts/sign", json={"contract_id": contract["id"], "actor_id": seller["id"]})
    escrow = client.post("/escrow/create", json={"contract_id": contract["id"]}).json()

    task = client.post("/tasks/create", json={
        "requester_id": buyer["id"], "skill": "market-data",
        "contract_id": contract["id"],
        "acceptance_criteria": {"type": "text", "min_length": 500,
                                "must_include": ["impossible-token"]}}).json()
    client.post("/tasks/assign", json={"task_id": task["id"], "assignee_id": seller["id"]})
    client.post("/tasks/submit", json={"task_id": task["id"], "result": {"text": "too short"}})
    done = client.post("/tasks/complete", json={"task_id": task["id"]}).json()
    assert done["status"] == "failed"

    escrow_after = client.get(f"/escrow/{escrow['id']}").json()
    assert escrow_after["status"] == "refunded"
    buyer_after = client.get(f"/agents/{buyer['id']}").json()
    assert buyer_after["balance"] == 1000.0  # refunded in full


def test_demo_runs(client):
    client.post("/demo/seed")
    result = client.post("/demo/run").json()
    assert result["orchestrator"] == "ResearchAgent"
    assert len(result["hires"]) == 3
    assert result["total_paid_out"] > 0
