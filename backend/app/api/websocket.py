from fastapi import WebSocket
from typing import Dict, List
import json

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, run_id: str, websocket: WebSocket):
        await websocket.accept()
        if run_id not in self.active_connections:
            self.active_connections[run_id] = []
        self.active_connections[run_id].append(websocket)
    
    def disconnect(self, run_id: str, websocket: WebSocket):
        if run_id in self.active_connections:
            if websocket in self.active_connections[run_id]:
                self.active_connections[run_id].remove(websocket)
            if not self.active_connections[run_id]:
                del self.active_connections[run_id]
    
    async def broadcast(self, run_id: str, message: dict):
        if run_id in self.active_connections:
            # Create list copy to safely iterate while items might be removed
            websockets = list(self.active_connections[run_id])
            for connection in websockets:
                try:
                    await connection.send_text(json.dumps(message))
                except Exception:
                    self.disconnect(run_id, connection)

manager = ConnectionManager()
