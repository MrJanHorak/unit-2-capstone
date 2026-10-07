import sqlite3
import re
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

client = genai.Client()

SCHEMA_CONTEXT = """
Database Engine: SQLite (Must use standard SQLite dialect)

Available tables and schemas:
- sales(id INTEGER, region TEXT, product TEXT, revenue REAL, date TEXT [YYYY-MM-DD], units_sold INTEGER)
- customers(id INTEGER, name TEXT, industry TEXT, churn_date TEXT [YYYY-MM-DD], satisfaction_score REAL)
- employees(id INTEGER, department TEXT, satisfaction_score REAL, tenure_years INTEGER)

SQLite Date Function Rules:
- Use strftime('%Y-%m', date) for monthly groupings (Do NOT use DATE_TRUNC, MONTH(), or YEAR()).
- Use strftime('%Y', date) for yearly groupings.
- Use date >= '2025-10-01' AND date <= '2025-12-31' or strftime('%m', date) IN ('10', '11', '12') for Q4 filtering.
"""

def clean_sql_output(raw_sql: str) -> str:
    """Removes markdown code fences, backticks, and extra whitespace."""
    sql = re.sub(r"```(?:sql)?", "", raw_sql, flags=re.IGNORECASE)
    sql = sql.replace("```", "").strip("` \n\r\t")
    return sql

def validate_sql(query: str) -> dict:
    blocked = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE"]
    for word in blocked:
        if word in query.upper():
            return {"valid": False, "reason": f"Blocked keyword: {word}"}
    if not query.strip().upper().startswith("SELECT"):
        return {"valid": False, "reason": "Only SELECT queries are permitted"}
    return {"valid": True, "reason": "OK"}

def generate_sql(query: str) -> dict:
    prompt = f"""{SCHEMA_CONTEXT}

Generate a single SQLite SELECT query to answer the following user question:
"{query}"

CRITICAL RULES:
1. Return ONLY the raw executable SQL query string.
2. Do NOT include markdown code blocks, explanation, or extra text.
3. Use ONLY SQLite-compatible functions.
"""

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt,
        config=types.GenerateContentConfig(
            max_output_tokens=300
        )
    )

    sql_text = clean_sql_output(response.text or "")

    return {
        "sql": sql_text,
        "input_tokens": response.usage_metadata.prompt_token_count if response.usage_metadata else 0,
        "output_tokens": response.usage_metadata.candidates_token_count if response.usage_metadata else 0
    }

def run(query: str) -> dict:
    sql_result = generate_sql(query)
    sql = sql_result["sql"]
    validation = validate_sql(sql)

    if not validation["valid"]:
        return {
            "answer": f"Query blocked: {validation['reason']}",
            "sql": sql,
            "rows": [],
            "validation": "FAILED",
            "input_tokens": sql_result["input_tokens"],
            "output_tokens": sql_result["output_tokens"]
        }

    try:
        conn = sqlite3.connect("./data/database.sqlite")
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        cols = [d[0] for d in cursor.description] if cursor.description else []
        conn.close()

        # Use Gemini to interpret the results
        interpretation = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=f"The user asked: {query}\n\nSQL query used: {sql}\n\nResults:\nColumns: {cols}\nData: {rows[:20]}\n\nProvide a clear, concise interpretation of these results.",
            config=types.GenerateContentConfig(
                max_output_tokens=512
            )
        )

        input_tokens = sql_result["input_tokens"]
        output_tokens = sql_result["output_tokens"]
        if interpretation.usage_metadata:
            input_tokens += interpretation.usage_metadata.prompt_token_count
            output_tokens += interpretation.usage_metadata.candidates_token_count

        return {
            "answer": interpretation.text,
            "sql": sql,
            "columns": cols,
            "rows": rows,
            "validation": "PASSED",
            "input_tokens": input_tokens,
            "output_tokens": output_tokens
        }

    except Exception as e:
        return {
            "answer": f"Query execution failed: {str(e)}",
            "sql": sql,
            "rows": [],
            "validation": "ERROR",
            "input_tokens": sql_result["input_tokens"],
            "output_tokens": sql_result["output_tokens"]
        }