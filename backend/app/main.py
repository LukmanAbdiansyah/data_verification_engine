from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

from .database.engine import init_db
from .utils.logging import configure_logging
from .api.routes_checklist import router as checklist_router
from .api.routes_repository import router as repository_router
from .api.routes_validation import router as validation_router
from .api.routes_review import router as review_router
from .api.routes_settings import router as settings_router
from .api.routes_history import router as history_router
from .api.websocket import manager
from .api.routes_verification import router as verification_router, set_coordinator as set_verification_coordinator
from .api.routes_catalog import router as catalog_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    await init_db()
    from .verification.service import VerificationCoordinator
    coordinator = VerificationCoordinator()
    set_verification_coordinator(coordinator)
    yield

app = FastAPI(title="Seismic Deliverable Verification AI Checker", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(checklist_router, prefix="/api/checklist", tags=["Checklist"])
app.include_router(repository_router, prefix="/api/repository", tags=["Repository"])
app.include_router(validation_router, prefix="/api/validation", tags=["Validation"])
app.include_router(review_router, prefix="/api/review", tags=["Review"])
app.include_router(settings_router, prefix="/api/settings", tags=["Settings"])
app.include_router(history_router, prefix="/api/history", tags=["History"])
app.include_router(verification_router, prefix="/api/verification", tags=["Verification"])
app.include_router(catalog_router, prefix="/api/catalog", tags=["Catalog"])

@app.websocket("/ws/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str):
    await manager.connect(run_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(run_id, websocket)

@app.get("/")
def read_root():
    return {"status": "ok", "app": "Seismic Checker API"}
