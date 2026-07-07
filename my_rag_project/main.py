# main.py
import re
from memory import add_message, get_history
from llm import ask_llm
from .config import db  # Get the database from config
from .sync import sync_uploads_to_vector_db  # Get the sync tool

def reformulate_question_with_memory(question: str, history: str) -> str:
    if not history or not history.strip():
        return question

    prompt = f"""You are a conversational query rewriter.
Analyze the following conversation history and the new user question.
If the new user question contains ambiguous pronouns (like "it", "they", "that", "this"), relative references, or refers to previous messages, reformulate it into a self-contained, descriptive search query.
If the question is already specific and self-contained, return the question exactly as it is.

Conversation History:
{history}

New Question: "{question}"

Output ONLY the final reformulated self-contained question. Do not include any other text, prefix, or explanation.
Question:"""
    try:
        reformulated = ask_llm(prompt).strip().strip('"')
        if reformulated:
            return reformulated
    except Exception as e:
        print(f"Failed to reformulate question with memory: {e}")
    return question

def _classify_query_intent(question):
    prompt = f"""You are a query classifier routing agent for a company FAQ and document QA assistant.
Classify the user's query into exactly one of the following categories:
- GREETING: General conversational messages, greetings, social chit-chat (e.g. "hi", "hello", "thanks", "how are you").
- FAQ: Questions about company rules, working hours, benefits, policies, office location, etc.
- DOCUMENT: Questions about uploaded documents, PDFs, or files (e.g., "summarize this PDF", "what is written in sample.pdf", "read the text file").
- OTHER: Out-of-scope or general knowledge questions not related to the company or any document.

User Query: "{question}"

Output only the category name in uppercase (GREETING, FAQ, DOCUMENT, or OTHER). Do not include any other text, explanation, or punctuation.
Category:"""
    try:
        intent = ask_llm(prompt).strip().upper()
        for category in ["GREETING", "FAQ", "DOCUMENT", "OTHER"]:
            if category in intent:
                return category
        return "OTHER"
    except Exception as e:
        print(f"Routing classifier failed: {e}")
        return "OTHER"


def search_faq(query: str) -> str:
    try:
        results = db.similarity_search(query, k=3)
        return "\n\n".join([doc.page_content for doc in results])
    except Exception as e:
        return f"Error searching FAQ: {e}"


def search_document(query: str, file_name: str) -> str:
    try:
        results = db.similarity_search(query, k=3, filter={"source": file_name})
        return "\n\n".join([doc.page_content for doc in results])
    except Exception as e:
        return f"Error searching document {file_name}: {e}"


def rewrite_query(query: str) -> str:
    prompt = f"""You are a query rewriter. Rewrite the following user search query to contain descriptive keywords suitable for semantic search. Do not answer the question.

Original: "{query}"

Output only the rewritten search query. Do not include any other explanation.
Rewritten Query:"""
    try:
        return ask_llm(prompt).strip().strip('"')
    except Exception as e:
        return query


def check_context_relevance(question: str, context: str) -> bool:
    if not context or not context.strip():
        return False
    prompt = f"""You are a relevance evaluator.
Does the following Context contain any information related to the Question?
Question: {question}
Context: {context}

Reply with YES or NO.
Answer:"""
    try:
        response = ask_llm(prompt).strip().upper()
        return "NO" not in response
    except Exception as e:
        print(f"Relevance check failed: {e}")
        return True


def audit_answer(question: str, context: str, answer_text: str) -> bool:
    prompt = f"""You are an answer auditing evaluator checking for hallucinations.
Verify if the draft answer is strictly grounded in and supported by the retrieved context.
If the answer makes any claims, dates, names, or numbers that are NOT explicitly mentioned in the context, output NO.
Otherwise, if the answer is fully grounded in the context, output YES.

Retrieved Context:
{context}

Draft Answer:
{answer_text}

Output only YES or NO. Do not include any other characters or explanation.
Grounded:"""
    try:
        response = ask_llm(prompt).strip().upper()
        return "YES" in response
    except Exception as e:
        print(f"Auditing failed: {e}")
        return True  # Fallback to True if LLM fails


def agent_executor(question):
    context = ""
    history = []

    # Run up to 2 turns
    for turn in range(2):
        prompt = f"""You are an assistant. Answer the question using context or tools.
Available Tools:
- Search_FAQ(query): Search company policies, working hours, benefits, and general databases.
- Rewrite_Query(query): Rewrite a vague question for better searching.

History:
{chr(10).join(history)}

Current Context:
{context or "No search context retrieved yet."}

User Question: {question}

To call a tool, output exactly: TOOL: <ToolName>(<arguments>)
Example: TOOL: Search_FAQ(working hours)

To answer the question, output exactly: ANSWER: <your answer>
Example: ANSWER: Our working hours are 9 AM to 5 PM.

IMPORTANT: Always search the database first using Search_FAQ before deciding to rewrite queries.

What is your next action? Output ONLY one line starting with TOOL: or ANSWER:."""

        try:
            response = ask_llm(prompt).strip()
        except Exception as e:
            print(f"Agent prompt failed: {e}")
            break

        print(f"Agent Turn {turn+1}: {response}")

        if response.startswith("ANSWER:"):
            draft = response.replace("ANSWER:", "").strip()
            # Audit draft answer
            if context and not audit_answer(question, context, draft):
                print("Auditor flagged draft answer as unsupported/hallucination! Regenerating...")
                # Try regenerating once with strict instruction
                prompt_strict = f"""You are a helpful assistant. Use the following context to answer the user's question.
IMPORTANT: Your previous attempt was audited and flagged for containing claims not supported by the context.
Ensure your response is STRICTLY grounded in the provided context. If the context does not contain the answer, say "I cannot find the answer in the provided documents."

Context:
{context}

Question: {question}
Answer:"""
                try:
                    draft = ask_llm(prompt_strict).strip()
                except Exception:
                    pass
            return draft

        elif response.startswith("TOOL:"):
            tool_call = response.replace("TOOL:", "").strip()
            match = re.match(r"(\w+)\((.*)\)", tool_call)
            if match:
                tool_name, tool_arg = match.groups()
                tool_arg = tool_arg.strip()

                if tool_name == "Search_FAQ":
                    result = search_faq(tool_arg)
                    
                    # Relevance Check
                    if not check_context_relevance(tool_arg, result):
                        print(f"Context retrieved for '{tool_arg}' flagged as irrelevant. Rewriting query...")
                        rewritten = rewrite_query(tool_arg)
                        result = search_faq(rewritten)
                        history.append(f"Action: Call Search_FAQ('{tool_arg}') -> Result: Context irrelevant. Rewrote to '{rewritten}' and searched again.")
                    else:
                        history.append(f"Action: Call Search_FAQ('{tool_arg}') -> Result: Found relevant FAQ information.")
                        
                    context += f"\n[FAQ Context for search '{tool_arg}']:\n{result}\n"
                elif tool_name == "Rewrite_Query":
                    rewritten = rewrite_query(tool_arg)
                    context += f"\n[Rewrite]: Query rewritten from '{tool_arg}' to '{rewritten}'\n"
                    history.append(f"Action: Call Rewrite_Query('{tool_arg}') -> Result: '{rewritten}'")
                    question = rewritten
                else:
                    context += f"\n[Error: Unknown tool '{tool_name}']\n"
                    history.append(f"Action: Unknown tool error.")
            else:
                context += f"\n[Error: Invalid format]\n"
                history.append(f"Action: Format error.")
        else:
            if len(response) > 0 and not response.isspace():
                if context and not audit_answer(question, context, response):
                    print("Auditor flagged conversational response as unsupported!")
                return response

    final_prompt = f"""You are a helpful assistant. Use the following context to answer the user's question.
If the context does not contain the answer, say "I cannot find the answer in the provided documents."

Context:
{context}

Question: {question}
Answer:"""
    try:
        draft = ask_llm(final_prompt).strip()
        if context and not audit_answer(question, context, draft):
            print("Auditor flagged final fallback answer! Regenerating...")
            strict_prompt = f"""You are a helpful assistant. Use the following context to answer the user's question.
IMPORTANT: Ensure your response is STRICTLY grounded in the provided context. If the context does not contain the answer, say "I cannot find the answer in the provided documents."

Context:
{context}

Question: {question}
Answer:"""
            draft = ask_llm(strict_prompt).strip()
        return draft
    except Exception as e:
        return f"Error generating final response: {str(e)}"


def answer(question, file_name=None):
    history = get_history()

    if not question or not question.strip():
        response = "Please ask a question about the company FAQ or your uploaded documents."
        add_message("User", question)
        add_message("Assistant", response)
        return response

    # Call our sync tool from the other file
    sync_uploads_to_vector_db()

    # Reformulate question based on history (Context-Aware Memory)
    original_question = question
    question = reformulate_question_with_memory(question, history)
    if question != original_question:
        print(f"Reformulated query from conversational context: '{original_question}' -> '{question}'")

    # Route logic
    if file_name and file_name != "Default (FAQs & All Documents)":
        # Direct document QA pathway (bypasses agent loop for fast, exact document lookup)
        try:
            results = db.similarity_search(question, k=4, filter={"source": file_name})
            if results:
                context = "\n\n".join([doc.page_content for doc in results])
            else:
                context = ""
        except Exception as e:
            print(f"Error querying Chroma: {e}")
            context = ""

        if context:
            prompt = f"""You are a helpful assistant. Use the following context from the document "{file_name}" to answer the user's question.
If the context does not contain the answer, say "I cannot find the answer in the provided documents."

Context:
{context}

Question: {question}
Answer:"""
            try:
                response = ask_llm(prompt).strip()
                # Audit answer for direct document QA path
                if not audit_answer(question, context, response):
                    print("Auditor flagged direct document QA answer! Regenerating with strict constraint...")
                    strict_prompt = f"""You are a helpful assistant. Use the following context from the document "{file_name}" to answer the user's question.
IMPORTANT: Ensure your response is STRICTLY grounded in the provided context. If the context does not contain the answer, say "I cannot find the answer in the provided documents."

Context:
{context}

Question: {question}
Answer:"""
                    response = ask_llm(strict_prompt).strip()
            except Exception as e:
                response = f"Error querying LLM: {str(e)}"
        else:
            response = "I don't have information about that."
    else:
        intent = _classify_query_intent(question)
        print(f"Query: '{question}' routed to: {intent}")

        if intent == "GREETING":
            prompt = f"Respond politely and conversationally to the user's greeting/chit-chat:\n\nUser: {question}\nResponse:"
            try:
                response = ask_llm(prompt).strip()
            except Exception as e:
                response = f"Hello! How can I help you today? (LLM error: {str(e)})"
        elif intent == "OTHER":
            response = "I can only answer questions related to the company FAQs or your uploaded documents. Please ask a relevant question."
        else:
            response = agent_executor(question)

    add_message("User", question)
    add_message("Assistant", response)
    return response