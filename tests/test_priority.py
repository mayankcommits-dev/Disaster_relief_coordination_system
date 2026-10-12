from types import SimpleNamespace

from backend.services.priority import calculate_priority_score


def test_critical_emergency():
    emergency = SimpleNamespace(
        people_trapped=True,
        immediate_danger=True,
        rising_water=True,
        injured_people=1,
        children=2,
        elderly_people=0,
        people_affected=5,
    )

    score, priority, reasons = calculate_priority_score(emergency)

    assert score == 100
    assert priority == "CRITICAL"


def test_normal_emergency():
    emergency = SimpleNamespace(
        people_trapped=False,
        immediate_danger=False,
        rising_water=False,
        injured_people=0,
        children=0,
        elderly_people=0,
        people_affected=2,
    )

    score, priority, reasons = calculate_priority_score(emergency)

    assert score == 0
    assert priority == "NORMAL"