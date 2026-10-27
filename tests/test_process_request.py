import main
from classifier import Ticket
from tests.fakes import FakeLLM

LEAK = Ticket(is_hostel_related=True, category="plumbing", urgency="high", location="D-112", summary="Ceiling leak.")


def setup(monkeypatch, history=None, insert_error=None):
    calls = {"fetch": [], "insert": []}

    def fake_fetch(reg_number, limit=10):
        calls["fetch"].append(reg_number)
        return history or []

    def fake_insert(name, reg_number, ticket):
        if insert_error:
            raise insert_error
        calls["insert"].append((name, reg_number, ticket))

    monkeypatch.setattr(main, "fetch_problem_statements", fake_fetch)
    monkeypatch.setattr(main, "insert_request", fake_insert)
    return calls


def test_hostel_complaint_is_recorded(monkeypatch):
    calls = setup(monkeypatch)
    result = main.process_hostel_request("Asha", "21BCE001", "ceiling leaking in D-112", FakeLLM([LEAK]))
    assert result.status == "recorded"
    assert calls["insert"] == [("Asha", "21BCE001", LEAK)]


def test_off_topic_message_is_rejected_not_stored(monkeypatch):
    calls = setup(monkeypatch)
    llm = FakeLLM([Ticket(is_hostel_related=False)])
    result = main.process_hostel_request("Asha", "21BCE001", "when is the DBMS deadline?", llm)
    assert result.status == "rejected"
    assert calls["insert"] == []


def test_model_failure_is_an_error_not_a_rejection(monkeypatch):
    calls = setup(monkeypatch)
    llm = FakeLLM([ValueError("bad"), ValueError("bad")])
    result = main.process_hostel_request("Asha", "21BCE001", "leak", llm)
    assert result.status == "error"
    assert calls["insert"] == []


def test_database_failure_is_reported(monkeypatch):
    setup(monkeypatch, insert_error=RuntimeError("db down"))
    result = main.process_hostel_request("Asha", "21BCE001", "leak", FakeLLM([LEAK]))
    assert result.status == "error"


def test_only_this_students_history_reaches_the_model(monkeypatch):
    calls = setup(monkeypatch, history=[{"problem_statement": "Wifi is slow."}])
    llm = FakeLLM([LEAK])
    main.process_hostel_request("Asha", "21BCE001", "leak", llm)

    assert calls["fetch"] == ["21BCE001"]
    prompt = llm.structured.calls[0][1].content
    assert "- Wifi is slow." in prompt
