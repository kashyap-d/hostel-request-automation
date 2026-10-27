from typing import get_args

from classifier import Category, Ticket, Urgency
from evals.run_eval import load_cases, location_matches, score_case, summarize


def test_location_word_order_does_not_matter():
    assert location_matches("room 214, B block", "B-block, Room 214")


def test_location_must_contain_expected_words():
    assert not location_matches("room 214, B block", "room 214")


def test_invented_location_fails_when_none_was_given():
    assert location_matches(None, None)
    assert not location_matches(None, "room 101")


def test_missing_ticket_fails_only_the_produced_check():
    case = {"id": "x", "expected": {"is_hostel_related": True, "category": "plumbing", "urgency": "low"}}
    assert score_case(case, None) == {"produced_ticket": False}


def test_list_of_acceptable_values():
    case = {"id": "x", "expected": {"is_hostel_related": True, "category": ["plumbing", "electrical"], "urgency": "medium"}}
    ticket = Ticket(is_hostel_related=True, category="electrical", urgency="medium", summary="Geyser broken.")
    checks = score_case(case, ticket)
    assert checks["category"] and checks["urgency"]


def test_injection_that_bumps_urgency_is_caught():
    case = {"id": "inj-x", "expected": {"is_hostel_related": True, "category": "electrical", "urgency": ["low", "medium"]}}
    ticket = Ticket(is_hostel_related=True, category="electrical", urgency="high", summary="AC not cooling.")
    assert score_case(case, ticket)["injection_resisted"] is False


def test_precision_and_recall():
    results = [
        {"expected": {"is_hostel_related": True}, "ticket": {"is_hostel_related": True}, "checks": {}, "latency_s": 1.0},
        {"expected": {"is_hostel_related": False}, "ticket": {"is_hostel_related": True}, "checks": {}, "latency_s": 2.0},
        {"expected": {"is_hostel_related": True}, "ticket": {"is_hostel_related": False}, "checks": {}, "latency_s": 3.0},
    ]
    summary = summarize(results)
    assert summary["accept_precision"] == 0.5
    assert summary["accept_recall"] == 0.5
    assert summary["latency_p50_s"] == 2.0


def test_dataset_labels_use_valid_values():
    cases = load_cases()
    assert len({c["id"] for c in cases}) == len(cases)
    for case in cases:
        expected = case["expected"]
        if not expected["is_hostel_related"]:
            continue
        for field, allowed in (("category", get_args(Category)), ("urgency", get_args(Urgency))):
            values = expected[field] if isinstance(expected[field], list) else [expected[field]]
            assert set(values) <= set(allowed), (case["id"], field)
