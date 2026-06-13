"""Registry, discovery, and reputation tests."""


def test_register_and_get(client):
    r = client.post("/agents/register", json={
        "name": "AlphaAgent", "skills": ["nlp", "summarization"], "price_per_task": 12})
    assert r.status_code == 201
    agent = r.json()
    assert agent["name"] == "AlphaAgent"
    assert agent["balance"] == 1000.0
    assert agent["reputation"] > 0

    got = client.get(f"/agents/{agent['id']}")
    assert got.status_code == 200
    assert got.json()["id"] == agent["id"]


def test_search_ranks_by_skill(client):
    client.post("/agents/register", json={
        "name": "CheapData", "skills": ["market-data"], "price_per_task": 5,
        "avg_latency_ms": 5000})
    client.post("/agents/register", json={
        "name": "FastData", "skills": ["market-data"], "price_per_task": 25,
        "avg_latency_ms": 500})
    r = client.get("/agents/search", params={"skill": "market-data"})
    assert r.status_code == 200
    results = r.json()
    assert len(results) >= 2
    assert all(res["match_score"] >= 0 for res in results)
    # Results must be sorted descending by match score.
    scores = [res["match_score"] for res in results]
    assert scores == sorted(scores, reverse=True)


def test_rating_updates_reputation(client):
    a = client.post("/agents/register", json={
        "name": "RatableAgent", "skills": ["x"]}).json()
    before = a["reputation"]
    r = client.post("/reputation/rate", json={"agent_id": a["id"], "rating": 5})
    assert r.status_code == 200
    body = r.json()
    assert body["total_ratings"] == 1
    assert body["trust_tier"] in {
        "unproven", "emerging", "established", "trusted", "elite"}
    assert body["reputation"] != before
