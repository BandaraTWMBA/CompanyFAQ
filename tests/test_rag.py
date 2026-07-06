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
