def find_resource_candidates(resources, required_type, people):
    candidates = []

    for resource in resources:

        if resource["type"] != required_type:
            continue

        if resource["status"] != "AVAILABLE":
            continue

        if required_type in ["RESCUE_BOAT", "SHELTER"]:
            if resource["capacity"] < people:
                continue

        candidates.append(resource)

    return candidates


def select_best_resource(resources, required_type, people):
    candidates = find_resource_candidates(
        resources,
        required_type,
        people,
    )

    if not candidates:
        return None

    return min(
        candidates,
        key=lambda resource: resource["distance_km"],
    )