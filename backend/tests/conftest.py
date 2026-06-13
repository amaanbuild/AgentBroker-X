"""Pytest fixtures - isolated in-memory database per test session."""
from __future__ import annotations

import os

os.environ["DATABASE_URL"] = "sqlite:///./test_agentbroker.db"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def _schema():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def two_agents(client):
    a = client.post("/agents/register", json={
        "name": "Buyer", "skills": ["research"], "price_per_task": 50}).json()
    b = client.post("/agents/register", json={
        "name": "Seller", "skills": ["market-data"], "price_per_task": 20}).json()
    return a, b
