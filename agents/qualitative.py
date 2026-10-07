import sqlite3
from google import genai
from google.genai import types  # Imported to support system instructions if needed
from dotenv import load_dotenv
load_dotenv()

client = genai.Client()

SCHEMA_CONTEXT = """
Available tables:
- sales(id, region, product, revenue, date, units_sold)
- customers(id, name, industry, churn_date, satisfaction_score)
- employees(id, department, satisfaction_score, tenure_years)
"""

def validate_sql(query: str) -> dict:
    blocked = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE"]
    for word in blocked:
        if word in query.upper():
            return {"valid": False, "reason": f"Blocked keyword: {word}"}
    if not query.strip().upper().startswith("SELECT"):
        return {"valid": False, "reason": "Only SELECT queries are permitted"}
    return {"valid": True, "reason": "OK"}

def generate_sql(query: str) -> dict:
    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=f"{SCHEMA_CONTEXT}\n\nGenerate a SQL query for: {query}\n\nReturn ONLY the SQL query, nothing else.",
        config=types.GenerateContentConfig(
            max_output_tokens=256
        )
    )
    
    # Strip any markdown code fences (like ```sql) that Gemini frequently adds
    sql_text = response.text.strip().strip("`").replace("sql\n", "").strip()
    
    return {
        "sql": sql_text,
        "input_tokens": response.usage_metadata.prompt_token_count,
        "output_tokens": response.usage_metadata.candidates_token_count
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
        cols = [d[0] for d in cursor.description]
        conn.close()

        # Use Gemini to interpret the results
        interpretation = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=f"The user asked: {query}\n\nSQL query used: {sql}\n\nResults:\nColumns: {cols}\nData: {rows[:20]}\n\nProvide a clear, concise interpretation of these results.",
            config=types.GenerateContentConfig(
                max_output_tokens=512
            )
        )

        return {
            "answer": interpretation.text,
            "sql": sql,
            "columns": cols,
            "rows": rows,
            "validation": "PASSED",
            "input_tokens": sql_result["input_tokens"] + interpretation.usage_metadata.prompt_token_count,
            "output_tokens": sql_result["output_tokens"] + interpretation.usage_metadata.candidates_token_count
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