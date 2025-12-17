import os
import sys

# ensure repository root is on sys.path so `src` package can be imported
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fastapi.testclient import TestClient

from drillapi.app import app
from drillapi.routes.cantons import get_cantons_data, filter_active_cantons

client = TestClient(app)


def test_get_all_cantons():
    """
    Test that GET /v1/cantons returns the full cantons dictionary.
    """
    response = client.get("/v1/cantons")
    assert response.status_code == 200
    data = response.json()
    # Should be a dictionary with some keys
    assert isinstance(data, dict)
    # Check that known cantons exist
    assert "ZH" in data
    assert "BE" in data


def test_get_specific_canton():
    """
    Test that GET /v1/cantons/{code} returns the correct canton.
    """
    response = client.get("/v1/cantons/ZH")
    assert response.status_code == 200
    data = response.json()
    assert "ZH" in data
    assert data["ZH"]["name"] == "ZH"

    # test lowercase input is converted to uppercase
    response = client.get("/v1/cantons/be")
    assert response.status_code == 200
    data = response.json()
    assert "BE" in data
    assert data["BE"]["name"] == "BE"


def test_get_nonexistent_canton():
    """
    Test that GET /v1/cantons/{code} returns 404 for an invalid canton.
    """
    response = client.get("/v1/cantons/XX")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Canton 'XX' not found"


def test_invalid_canton_code_length():
    """
    Test that a path parameter with invalid length is rejected.
    """
    response = client.get("/v1/cantons/Z")
    assert response.status_code == 422  # validation error
    response = client.get("/v1/cantons/ZZZ")
    assert response.status_code == 422


def test_coord_x_out_of_range_returns_422():
    # coord_x must be > 2400000 per path annotation
    resp = client.get("/v1/drill-category/2000000/1200000")
    assert resp.status_code == 422


def test_coord_y_out_of_range_returns_422():
    # coord_y must be > 1070000 per path annotation
    resp = client.get("/v1/drill-category/2600000/1000000")
    assert resp.status_code == 422


def test_filter_active_cantons_returns_only_active():
    all_cantons = get_cantons_data()
    filtered = filter_active_cantons(all_cantons)

    # Ensure none of the returned cantons has active = False
    for code, cfg in filtered.items():
        assert cfg.get("active") is True

    assert "ZH" in filtered  # ZH is inactive
    assert "NE" not in filtered  # NE is inactive
    assert "VD" in filtered  # VD is active


def test_get_available_cantons_endpoint():
    response = client.get("/v1/avalaible-cantons")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert "ZH" in data
    assert "NE" not in data
    assert "VD" in data

    # Optionally, ensure no duplicates and result matches filter_active_cantons
    expected = sorted(list(filter_active_cantons(get_cantons_data()).keys()))
    assert sorted(data) == expected
