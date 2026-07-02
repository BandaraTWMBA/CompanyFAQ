from pathlib import Path
import re

from memory import add_message, get_history


FAQ_PATH = Path(__file__).resolve().parent / "data" / "company_faqs.txt"


def _load_faqs():
    text = FAQ_PATH.read_text(encoding="utf-8")
    blocks = re.split(r"\n\s*---\s*\n", text.strip())

    faqs = []
    for block in blocks:
        if not block.strip():
            continue

        match = re.match(r"Q:\s*(.+?)\s*\n\s*A:\s*(.+)", block, re.S)
        if match:
            faqs.append((match.group(1).strip(), match.group(2).strip()))

    return faqs


FAQS = _load_faqs()


def _normalize(text):
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _score_question(query, faq_question):
    query_tokens = set(_normalize(query).split())
    faq_tokens = set(_normalize(faq_question).split())
    overlap = len(query_tokens & faq_tokens)

    if _normalize(query) in _normalize(faq_question):
        overlap += 3

    return overlap


def answer(question):
    history = get_history()

    if not question or not question.strip():
        response = "Please ask a question about the company FAQ."
    else:
        normalized_question = _normalize(question)

        response = None
        for faq_question, faq_answer in FAQS:
            normalized_faq_question = _normalize(faq_question)
            if normalized_question == normalized_faq_question:
                response = faq_answer
                break
            if normalized_question in normalized_faq_question or normalized_faq_question in normalized_question:
                response = faq_answer
                break

        if response is None:
            best_match = None
            best_score = 0
            for faq_question, faq_answer in FAQS:
                score = _score_question(question, faq_question)
                if score > best_score:
                    best_score = score
                    best_match = faq_answer

            response = best_match or "I don't have information about that."

    add_message("User", question)
    add_message("Assistant", response)
    return response