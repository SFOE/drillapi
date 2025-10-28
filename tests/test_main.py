import os
import sys

# ensure repository root is on sys.path so `src` package can be imported
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fastapi.testclient import TestClient

from src.main import app


client = TestClient(app)


def test_get_cantons_returns_list():
    resp = client.get("/v1/cantons")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    # basic sanity: expect at least one canton and specific canton present
    assert any(isinstance(item.get("name"), str) for item in data)
    assert any(item.get("name") == "ZH" for item in data)


def test_get_coords_ok():
    # use coordinates that appear in settings examples (should be within bounds)
    resp = client.get("/v1/2679004/1247702")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["coord_x"] == 2679004.0 or payload["coord_x"] == 2679004
    assert payload["coord_y"] == 1247702.0 or payload["coord_y"] == 1247702
    # current implementation returns Not Implemented
    assert payload.get("drill_category") == "Not Implemented"


def test_coord_x_out_of_range_returns_422():
    # coord_x must be > 2400000 per path annotation
    resp = client.get("/v1/2000000/1200000")
    assert resp.status_code == 422


def test_coord_y_out_of_range_returns_422():
    # coord_y must be > 1070000 per path annotation
    resp = client.get("/v1/2600000/1000000")
    assert resp.status_code == 422
