"""VirtualBoard: a DisplaySink that lives in the browser.

render() pushes the grid to every connected browser tab over WebSocket;
the page (static/board.js) owns the flip animation. The board also keeps
the latest grid so a tab that connects late still shows the current state.
"""

from clapper_ai.domain.grid import Grid, blank_grid


class VirtualBoard:
    def __init__(self, rows: int = 6, cols: int = 22):
        self.rows = rows
        self.cols = cols
        self.latest: Grid = blank_grid(rows, cols)
        self._clients: set = set()  # objects with an async send_json()

    async def attach(self, websocket) -> None:
        """Register a browser connection and bring it up to date."""
        self._clients.add(websocket)
        await websocket.send_json(self._message())

    def detach(self, websocket) -> None:
        self._clients.discard(websocket)

    async def render(self, grid: Grid) -> None:
        self.latest = grid
        for websocket in list(self._clients):
            try:
                await websocket.send_json(self._message())
            except Exception:
                # The tab closed or the connection dropped; forget it.
                self.detach(websocket)

    def _message(self) -> dict:
        return {"rows": self.rows, "cols": self.cols, "grid": self.latest}
