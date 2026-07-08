"""FastAPI app for the virtual board: one page, one WebSocket."""

from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from clapper_ai.displays.virtual.sink import VirtualBoard

STATIC_DIR = Path(__file__).parent / "static"


def create_app(board: VirtualBoard) -> FastAPI:
    app = FastAPI(title="clapper-ai virtual board")

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.websocket("/ws")
    async def ws(websocket: WebSocket) -> None:
        await websocket.accept()
        await board.attach(websocket)
        try:
            # The browser never sends anything; this loop just keeps the
            # connection open until the tab disconnects.
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            board.detach(websocket)

    return app
