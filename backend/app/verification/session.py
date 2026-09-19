import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any
from .inventory import FileInventory

@dataclass
class SessionState:
    result: dict[str, Any] | None = None
    inventory: FileInventory | None = None
    last_tool: str | None = None
    last_args: dict[str, Any] = field(default_factory=dict)
    updated_at: float = field(default_factory=time.time)

class VerificationSessionStore:
    def __init__(self, ttl_seconds: int = 1800):
        self._ttl = ttl_seconds
        self._store: dict[str, SessionState] = {}
        self._lock = threading.Lock()
    
    def get(self, session_id: str | None) -> SessionState:
        with self._lock:
            self._cleanup()
            if session_id and session_id in self._store:
                state = self._store[session_id]
                state.updated_at = time.time()
                return state
            return SessionState()
    
    def save(self, session_id: str, state: SessionState) -> None:
        with self._lock:
            state.updated_at = time.time()
            self._store[session_id] = state
            self._cleanup()
    
    def _cleanup(self) -> None:
        now = time.time()
        expired = [sid for sid, state in self._store.items() if now - state.updated_at > self._ttl]
        for sid in expired:
            del self._store[sid]
