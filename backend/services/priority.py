def calculate_priority_score(analysis):
    score = 0
    reasons = []

    if analysis.people_trapped:
        score += 30
        reasons.append(("People trapped", 30))

    if analysis.immediate_danger:
        score += 20
        reasons.append(("Immediate danger", 20))

    if analysis.rising_water:
        score += 20
        reasons.append(("Rising water", 20))

    if analysis.injured_people > 0:
        score += 20
        reasons.append(("Injured people", 20))

    if analysis.children > 0:
        score += 10
        reasons.append(("Children involved", 10))

    if analysis.elderly_people > 0:
        score += 10
        reasons.append(("Elderly people", 10))

    if analysis.people_affected >= 10:
        score += 10
        reasons.append(("Large group", 10))

    score = min(score, 100)

    if score >= 75:
        priority = "CRITICAL"
    elif score >= 45:
        priority = "HIGH"
    elif score >= 20:
        priority = "MEDIUM"
    else:
        priority = "NORMAL"

    return score, priority, reasons