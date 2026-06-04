"""Tests for canton routes and input validation.

Tests the HTTP API endpoints directly without importing internal functions.
"""


def test_get_all_cantons(client):
    """GET /v1/cantons returns the full cantons dictionary."""
    response = client.get("/v1/cantons")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "ZH" in data
    assert "BE" in data


def test_get_specific_canton(client):
    """GET /v1/cantons/{code} returns the correct canton."""
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


def test_get_nonexistent_canton(client):
    """GET /v1/cantons/{code} returns 404 for an invalid canton."""
    response = client.get("/v1/cantons/XX")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Canton 'XX' not found"


def test_invalid_canton_code_length(client):
    """Path parameter with invalid length is rejected with 422."""
    response = client.get("/v1/cantons/Z")
    assert response.status_code == 422
    response = client.get("/v1/cantons/ZZZ")
    assert response.status_code == 422


def test_coord_x_out_of_range_returns_422(client):
    """coord_x must be > 2400000 per path annotation."""
    resp = client.get("/v1/drill-category/2000000/1200000")
    assert resp.status_code == 422


def test_coord_y_out_of_range_returns_422(client):
    """coord_y must be > 1070000 per path annotation."""
    resp = client.get("/v1/drill-category/2600000/1000000")
    assert resp.status_code == 422


def test_available_cantons_returns_only_active(client):
    """GET /v1/avalaible-cantons returns only active canton codes."""
    response = client.get("/v1/avalaible-cantons")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)

    # Verify against the full config — all returned cantons must be active
    all_cantons_response = client.get("/v1/cantons")
    all_cantons = all_cantons_response.json()

    for code in data:
        assert all_cantons[code].get("active") is True, (
            f"Canton {code} returned by /v1/avalaible-cantons but is not active"
        )

    # Known active cantons should be present
    assert "ZH" in data
    assert "VD" in data

    # Known inactive cantons should be absent
    assert "NE" not in data
