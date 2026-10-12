from backend.services.matching import select_best_resource


def test_selects_closest_suitable_boat():
    resources = [
        {
            "id": "BOAT-01",
            "type": "RESCUE_BOAT",
            "capacity": 8,
            "distance_km": 8.4,
            "status": "AVAILABLE",
        },
        {
            "id": "BOAT-02",
            "type": "RESCUE_BOAT",
            "capacity": 6,
            "distance_km": 2.3,
            "status": "AVAILABLE",
        },
    ]

    result = select_best_resource(
        resources,
        "RESCUE_BOAT",
        5,
    )

    assert result["id"] == "BOAT-02"


def test_rejects_insufficient_capacity():
    resources = [
        {
            "id": "BOAT-01",
            "type": "RESCUE_BOAT",
            "capacity": 4,
            "distance_km": 1.0,
            "status": "AVAILABLE",
        },
        {
            "id": "BOAT-02",
            "type": "RESCUE_BOAT",
            "capacity": 8,
            "distance_km": 5.0,
            "status": "AVAILABLE",
        },
    ]

    result = select_best_resource(
        resources,
        "RESCUE_BOAT",
        6,
    )

    assert result["id"] == "BOAT-02"


def test_returns_none_when_no_resource_available():
    resources = [
        {
            "id": "BOAT-01",
            "type": "RESCUE_BOAT",
            "capacity": 10,
            "distance_km": 1.0,
            "status": "BUSY",
        }
    ]

    result = select_best_resource(
        resources,
        "RESCUE_BOAT",
        5,
    )

    assert result is None