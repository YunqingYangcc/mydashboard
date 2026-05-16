from kb.signals import _evaluate


def test_evaluate_lte_positive():
    status, direction, score = _evaluate("lte", 30.0, 35.0)
    assert status == "triggered"
    assert direction == "positive"
    assert score == 1


def test_evaluate_gte_negative():
    status, direction, score = _evaluate("gte", 0.5, 1.0)
    assert status == "triggered"
    assert direction == "negative"
    assert score == -1
