import pytest
from fastapi.testclient import TestClient

from app.agents.orchestrator import Orchestrator
from app.config import Settings
from app.main import create_app
from app.memory.store import MemoryStore
from app.tools import registry


@pytest.fixture
def orch():
    registry.TICKETS.clear()
    registry.ESCALATIONS.clear()
    return Orchestrator(Settings(), memory=MemoryStore(":memory:"))


@pytest.fixture
def client(orch):
    return TestClient(create_app(orch))
