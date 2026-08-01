"""Tests for the VirtualBoard sink and its FastAPI server."""

from fastapi.testclient import TestClient

from clapper_ai.adapters.displays.virtual.server import create_app
from clapper_ai.adapters.displays.virtual.sink import VirtualBoard


class FakeSocket:
    """Stands in for a browser WebSocket connection."""

    def __init__(self, fail: bool = False):
        self.fail = fail
        self.sent: list[dict] = []

    async def send_json(self, message: dict) -> None:
        if self.fail:
            raise RuntimeError("connection lost")
        self.sent.append(message)


async def test_new_client_immediately_receives_the_current_grid():
    board = VirtualBoard(rows=2, cols=3)
    socket = FakeSocket()

    await board.attach(socket)

    assert socket.sent == [{"rows": 2, "cols": 3, "grid": [[0, 0, 0], [0, 0, 0]]}]


async def test_render_broadcasts_to_every_client():
    board = VirtualBoard(rows=1, cols=2)
    first, second = FakeSocket(), FakeSocket()
    await board.attach(first)
    await board.attach(second)

    await board.render([[1, 2]])

    assert first.sent[-1]["grid"] == [[1, 2]]
    assert second.sent[-1]["grid"] == [[1, 2]]


async def test_render_with_no_clients_is_fine():
    board = VirtualBoard(rows=1, cols=1)
    await board.render([[5]])  # nobody watching yet — must not raise
    assert board.latest == [[5]]


async def test_dead_client_is_dropped_and_others_still_update():
    board = VirtualBoard(rows=1, cols=1)
    dead, alive = FakeSocket(fail=True), FakeSocket()
    board._clients.add(dead)  # attach() would fail; wire it in directly
    await board.attach(alive)

    await board.render([[3]])

    assert alive.sent[-1]["grid"] == [[3]]
    assert dead not in board._clients


def test_index_page_serves_the_board():
    app = create_app(VirtualBoard(rows=6, cols=22))
    response = TestClient(app).get("/")
    assert response.status_code == 200
    assert "board.js" in response.text


def test_websocket_route_sends_the_grid_on_connect():
    board = VirtualBoard(rows=1, cols=2)
    app = create_app(board)
    with TestClient(app).websocket_connect("/ws") as socket:
        message = socket.receive_json()
    assert message == {"rows": 1, "cols": 2, "grid": [[0, 0]]}
