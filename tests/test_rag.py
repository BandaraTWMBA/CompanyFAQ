from rag import answer


def test_answer_returns_faq_content_from_text_file():
    response = answer("What are your working hours?")

    assert "Monday to Friday" in response
    assert "9 AM" in response
