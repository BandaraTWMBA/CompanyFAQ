from pathlib import Path

from my_rag_project.main import answer


def test_answer_returns_faq_content_from_text_file():
    response = answer("What are your working hours?")

    assert "Monday to Friday" in response
    assert "9 AM" in response


def test_answer_can_use_uploaded_document_content(tmp_path):
    document_path = tmp_path / "notes.txt"
    document_path.write_text("The onboarding process takes two weeks.", encoding="utf-8")

    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)
    target_path = upload_dir / "notes.txt"
    target_path.write_text(document_path.read_text(encoding="utf-8"), encoding="utf-8")

    try:
        response = answer("How long is the onboarding process?")
        assert "two weeks" in response.lower()
    finally:
        if target_path.exists():
            target_path.unlink()


def test_answer_specific_file_uses_llm_with_context():
    from unittest.mock import patch
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)

    file_a = upload_dir / "doc_a.txt"
    file_b = upload_dir / "doc_b.txt"

    file_a.write_text("Secret code for project A is 12345.", encoding="utf-8")
    file_b.write_text("Secret code for project B is 99999.", encoding="utf-8")

    try:
        with patch("my_rag_project.main.ask_llm") as mock_ask:
            mock_ask.return_value = "Mocked answer"

            # Ask doc_a
            ans = answer("What is the secret code?", file_name="doc_a.txt")
            assert ans == "Mocked answer"

            # Check what context was passed to ask_llm
            args, kwargs = mock_ask.call_args
            prompt = args[0]
            assert "doc_a.txt" in prompt
            assert "12345" in prompt
            assert "99999" not in prompt

            mock_ask.reset_mock()

            # Ask doc_b
            ans = answer("What is the secret code?", file_name="doc_b.txt")
            assert ans == "Mocked answer"

            args, kwargs = mock_ask.call_args
            prompt = args[0]
            assert "doc_b.txt" in prompt
            assert "99999" in prompt
            assert "12345" not in prompt

    finally:
        if file_a.exists():
            file_a.unlink()
        if file_b.exists():
            file_b.unlink()


def test_routing_agent_greeting_intent():
    from unittest.mock import patch

    with patch("my_rag_project.main._classify_query_intent") as mock_classify, \
         patch("my_rag_project.main.ask_llm") as mock_ask, \
         patch("my_rag_project.main.db.similarity_search") as mock_search:

        mock_classify.return_value = "GREETING"
        mock_ask.return_value = "Hello! Nice to meet you."

        response = answer("Hi")
        assert response == "Hello! Nice to meet you."
        mock_search.assert_not_called()


def test_routing_agent_other_intent():
    from unittest.mock import patch

    with patch("my_rag_project.main._classify_query_intent") as mock_classify, \
         patch("my_rag_project.main.db.similarity_search") as mock_search:

        mock_classify.return_value = "OTHER"

        response = answer("Who is Isaac Newton?")
        assert "only answer questions related to the company FAQs" in response
        mock_search.assert_not_called()


def test_agent_executor_react_loop():
    from unittest.mock import patch
    from my_rag_project.main import agent_executor

    with patch("my_rag_project.main.ask_llm") as mock_ask, \
         patch("my_rag_project.main.search_faq") as mock_search_faq, \
         patch("my_rag_project.main.check_context_relevance", return_value=True), \
         patch("my_rag_project.main.audit_answer", return_value=True):

        mock_ask.side_effect = [
            "TOOL: Search_FAQ(holiday policy)",
            "ANSWER: We have 25 days of annual leaves."
        ]
        mock_search_faq.return_value = "Holiday policy: 25 days of annual leave."

        response = agent_executor("How many holidays do we get?")

        assert response == "We have 25 days of annual leaves."
        mock_search_faq.assert_called_once_with("holiday policy")
        assert mock_ask.call_count == 2


def test_self_correction_relevance_check():
    from unittest.mock import patch
    from my_rag_project.main import agent_executor

    with patch("my_rag_project.main.ask_llm") as mock_ask, \
         patch("my_rag_project.main.search_faq") as mock_search_faq, \
         patch("my_rag_project.main.check_context_relevance") as mock_relevance, \
         patch("my_rag_project.main.rewrite_query") as mock_rewrite, \
         patch("my_rag_project.main.audit_answer", return_value=True):

        # Turn 1: call tool
        # Turn 2: answer
        mock_ask.side_effect = [
            "TOOL: Search_FAQ(working hours)",
            "ANSWER: Working hours are 9 AM to 5 PM."
        ]
        mock_search_faq.side_effect = [
            "Irrelevant context info",
            "Working hours: 9 AM to 5 PM."
        ]
        mock_relevance.return_value = False
        mock_rewrite.return_value = "rewritten hours"

        response = agent_executor("What are working hours?")

        assert response == "Working hours are 9 AM to 5 PM."
        assert mock_rewrite.call_count == 1
        assert mock_search_faq.call_count == 2
        mock_search_faq.assert_any_call("working hours")
        mock_search_faq.assert_any_call("rewritten hours")


def test_self_correction_hallucination_audit():
    from unittest.mock import patch
    from my_rag_project.main import agent_executor

    with patch("my_rag_project.main.ask_llm") as mock_ask, \
         patch("my_rag_project.main.search_faq") as mock_search_faq, \
         patch("my_rag_project.main.audit_answer") as mock_audit, \
         patch("my_rag_project.main.check_context_relevance", return_value=True):

        mock_ask.side_effect = [
            "TOOL: Search_FAQ(vacation)",
            "ANSWER: You get 50 days of leaves.",
            "Corrected Answer: You get 25 days of leaves."
        ]
        mock_search_faq.return_value = "Vacation: 25 days of annual leave."
        mock_audit.side_effect = [False, True]

        response = agent_executor("How much vacation?")

        assert response == "Corrected Answer: You get 25 days of leaves."
        assert mock_audit.call_count == 1


def test_context_aware_memory_reformulation():
    from unittest.mock import patch
    from my_rag_project.main import reformulate_question_with_memory

    with patch("my_rag_project.main.ask_llm") as mock_ask:
        mock_ask.return_value = "Summarize Improving DES Security.pdf"

        history = "User: I uploaded Improving DES Security.pdf\nAssistant: File uploaded successfully.\n"
        response = reformulate_question_with_memory("Summarize it", history)

        assert response == "Summarize Improving DES Security.pdf"
        mock_ask.assert_called_once()
        args, _ = mock_ask.call_args
        assert "Summarize it" in args[0]
