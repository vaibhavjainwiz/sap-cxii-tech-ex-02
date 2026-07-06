import logging

from orders import db, llm

logger = logging.getLogger(__name__)


def ask(question: str) -> dict:
    """Answer a natural-language question using LLM-generated SQL."""
    total_tokens = 0

    # --- First attempt ---
    result, tokens = llm.generate_sql(question)
    total_tokens += tokens

    if result.get("out_of_scope"):
        return {
            "error": "unanswerable",
            "detail": result.get("reason", "The question cannot be answered from the available schema."),
        }

    sql = result.get("sql", "")

    # Try executing
    retry_error = None
    try:
        rows = db.execute_raw_sql(sql)
    except Exception as e:
        retry_error = str(e)

    # --- Retry once on error ---
    if retry_error is not None:
        logger.warning("SQL attempt 1 failed: %s — retrying", retry_error)
        result, tokens = llm.generate_sql(
            question, error_context=retry_error, prior_response=sql,
        )
        total_tokens += tokens

        if result.get("out_of_scope"):
            return {
                "error": "unanswerable",
                "detail": result.get("reason", "The question cannot be answered from the available schema."),
            }

        sql = result.get("sql", "")

        try:
            rows = db.execute_raw_sql(sql)
        except Exception as e2:
            return {
                "error": "sql_failed",
                "detail": f"SQL failed after retry: {e2}",
                "sql_used": sql,
            }

    # --- Build natural-language answer ---
    answer_text, answer_tokens = llm.generate_answer(question, sql, rows)
    total_tokens += answer_tokens
    logger.info("Total tokens for request: %d", total_tokens)

    return {
        "answer": answer_text,
        "sql_used": sql,
        "rows": rows[:100],
        "token_count": total_tokens,
    }
