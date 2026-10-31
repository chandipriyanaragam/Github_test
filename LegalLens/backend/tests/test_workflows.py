from app import workflows


def test_classify_maps_summarize_to_backend_summary(monkeypatch):
    monkeypatch.setattr(workflows, "_openai", lambda messages, json_mode=False: {"intent": "summarize"})

    assert workflows.classify("Summarize this agreement") == "summary"


def test_retrieve_ranks_matching_source_chunks():
    documents = [
        {"id": "general", "filename": "general.pdf", "pages": [(3, "The governing law applies to this agreement.")]},
        {"id": "notice", "filename": "notice.pdf", "pages": [(7, "The termination notice period is thirty days.")]},
    ]

    matches = workflows._retrieve("termination notice period", documents)

    assert matches[0]["document_id"] == "notice"
    assert matches[0]["page"] == 7
    assert "thirty days" in matches[0]["text"]
