from backend.services.matching import select_best_resource


def test_full_multi_resource_assignment():
    resources = [
        {
            "id": "BOAT-01",
            "name": "Rescue Boat",
            "type": "RESCUE_BOAT",
            "capacity": 8,
            "distance_km": 2.0,
            "status": "AVAILABLE",
        },
        {
            "id": "AMB-01",
            "name": "Ambulance",
            "type": "AMBULANCE",
            "capacity": 4,
            "distance_km": 3.0,
            "status": "AVAILABLE",
        },
        {
            "id": "MED-01",
            "name": "Medical Team",
            "type": "MEDICAL_TEAM",
            "capacity": 5,
            "distance_km": 4.0,
            "status": "AVAILABLE",
        },
    ]

    required = [
        "RESCUE_BOAT",
        "AMBULANCE",
        "MEDICAL_TEAM",
    ]

    assigned = []

    for resource_type in required:
        resource = select_best_resource(
            resources,
            resource_type,
            4,
        )

        if resource:
            assigned.append(resource["type"])

    assert set(assigned) == set(required)


def test_partial_assignment():
    resources = [
        {
            "id": "BOAT-01",
            "name": "Rescue Boat",
            "type": "RESCUE_BOAT",
            "capacity": 8,
            "distance_km": 2.0,
            "status": "AVAILABLE",
        },
        {
            "id": "SUP-01",
            "name": "Supply Team",
            "type": "SUPPLY_TEAM",
            "capacity": 100,
            "distance_km": 5.0,
            "status": "BUSY",
        },
    ]

    required = [
        "RESCUE_BOAT",
        "SUPPLY_TEAM",
    ]

    assigned = []

    for resource_type in required:
        resource = select_best_resource(
            resources,
            resource_type,
            4,
        )

        if resource:
            assigned.append(resource["type"])

    assert "RESCUE_BOAT" in assigned
    assert "SUPPLY_TEAM" not in assigned
    assert 0 < len(assigned) < len(required)


def test_waiting_when_no_resource_available():
    resources = [
        {
            "id": "BOAT-01",
            "name": "Rescue Boat",
            "type": "RESCUE_BOAT",
            "capacity": 8,
            "distance_km": 2.0,
            "status": "BUSY",
        }
    ]

    resource = select_best_resource(
        resources,
        "RESCUE_BOAT",
        4,
    )

    assert resource is None


def test_released_resource_can_be_reassigned():
    resources = [
        {
            "id": "BOAT-01",
            "name": "Rescue Boat",
            "type": "RESCUE_BOAT",
            "capacity": 8,
            "distance_km": 2.0,
            "status": "BUSY",
        }
    ]

    # Resource unavailable while handling another emergency.
    first_attempt = select_best_resource(
        resources,
        "RESCUE_BOAT",
        4,
    )

    assert first_attempt is None

    # Previous emergency is resolved and the resource is released.
    resources[0]["status"] = "AVAILABLE"

    second_attempt = select_best_resource(
        resources,
        "RESCUE_BOAT",
        4,
    )

    assert second_attempt is not None
    assert second_attempt["id"] == "BOAT-01"