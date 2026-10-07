from google import genai
from google.genai import types
from dotenv import load_dotenv
from agents import quantitative
from agents import qualitative
from validation.validator import validate_qualitative, validate_quantitative
from tokenomics.logger import log
load_dotenv()

client = genai.Client()

def classify(query: str) -> str:
    # 1. Changed client.messages.create -> client.models.generate_content
    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=f"""Classify this query as exactly one of: qualitative, quantitative, both.

qualitative = questions about policies, processes, procedures, explanations, documentation
quantitative = questions about numbers, metrics, trends, comparisons, SQL-queryable data
both = questions that need both document search and data analysis

Query: {query}

Reply with one word only: qualitative, quantitative, or both.""",
        config=types.GenerateContentConfig(
            max_output_tokens=512
        )
    )
    
    # 3. Changed response parsing to use standard .text
    route = response.text.strip().lower()
    
    # 4. Changed token logging syntax to use usage_metadata properties
    log(
        query, 
        "manager-classifier", 
        response.usage_metadata.prompt_token_count, 
        response.usage_metadata.candidates_token_count
    )
    
    return route if route in ["qualitative", "quantitative", "both"] else "qualitative"

def run(query: str):
    print(f"\nQuery: {query}")
    route = classify(query)
    print(f"Route: {route}")

    qual_result = None
    quant_result = None

    if route in ["qualitative", "both"]:
        qual_result = qualitative.run(query)
        validation = validate_qualitative(qual_result["answer"], qual_result["chunks"])
        log(query, "qualitative", qual_result["input_tokens"], qual_result["output_tokens"])
        if validation["flag"]:
            print(f"\n⚠️  VALIDATION WARNING: {validation['warning']}")
        print(f"\n[Qualitative]\n{qual_result['answer']}")

    if route in ["quantitative", "both"]:
        quant_result = quantitative.run(query)
        validation = validate_quantitative(
            quant_result["answer"],
            quant_result["sql"],
            quant_result["validation"]
        )
        log(query, "quantitative", quant_result["input_tokens"], quant_result["output_tokens"])
        if validation["flag"]:
            print(f"\n⚠️  VALIDATION WARNING: {validation['warning']}")
        print(f"\n[Quantitative]\n{quant_result['answer']}")
        print(f"SQL used: {quant_result['sql']}")
