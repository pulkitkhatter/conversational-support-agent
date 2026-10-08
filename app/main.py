from fastapi import FastAPI

from app.agents.orchestrator import Orchestrator
from app.api.routes import router
from app.config import get_settings


def create_app(orchestrator: Orchestrator | None = None) -> FastAPI:
    app = FastAPI(title="Production AI Support Agent", version="0.1.0")
    app.state.orchestrator = orchestrator or Orchestrator(get_settings())
    app.include_router(router)
    return app


app = create_app()
