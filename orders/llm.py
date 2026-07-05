import json
import logging

from openai import OpenAI

from orders.prompt import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI()  # reads OPENAI_API_KEY from env
    return _client


def _call_llm(messages: list[dict]) -> tuple[str, int]:
    client = _get_client()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0,
        max_tokens=512,
    )
    content = response.choices[0].message.content.strip()
    total_tokens = response.usage.total_tokens if response.usage else 0
    return content, total_tokens


def generate_sql(
    question: str,
    error_context: str | None = None,
    prior_response: str | None = None,
) -> tuple[dict, int]:
    """Convert a natural language question into SQL.

    Returns (parsed_json, token_count) where parsed_json has keys:
        out_of_scope (bool), reason (str|None), sql (str|None)

    If error_context and prior_response are provided, this is a retry
    attempt with the previous error appended to the conversation.
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    if prior_response and error_context:
        messages.append({"role": "assistant", "content": prior_response})
        messages.append(
            {
                "role": "user",
                "content": f"That SQL produced an error: {error_context}\nPlease fix the query.",
            }
        )

    raw, tokens = _call_llm(messages)
    logger.info("LLM generate_sql | question=%s | raw=%s | tokens=%d", question, raw, tokens)

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        result = {"out_of_scope": False, "reason": None, "sql": raw}

    return result, tokens


def generate_answer(question: str, sql: str, rows: list[dict]) -> tuple[str, int]:
    """Produce a human-readable answer from the SQL results."""
    prompt = (
        f'The user asked: "{question}"\n'
        f"The SQL query was: {sql}\n"
        f"The result rows are: {json.dumps(rows[:50])}\n\n"
        "Provide a concise, human-readable answer summarising the results. "
        "Include key numbers. Do not repeat the SQL."
    )
    answer, tokens = _call_llm([{"role": "user", "content": prompt}])
    logger.info("LLM generate_answer | tokens=%d", tokens)
    return answer, tokens
