"""Explicit live connectivity test; importing this file never makes an API call."""
from config import Settings
from llm import Gemini
from tokenomics.logger import Ledger


def main():
    settings = Settings.from_environment()
    ledger = Ledger("Connectivity smoke test: say hello in one sentence.", settings)
    status = "error"
    try:
        text = Gemini(settings, ledger).generate("smoke-test", "Say hello in one sentence.",
            system="This is a connectivity check. Reply with a brief greeting only.", max_tokens=128)
        if not text or len(text) > 500:
            raise ValueError("Unexpected smoke-test response")
        print(text)
        status = "accepted"
    finally:
        usage = ledger.finish("smoke-test", status)
        print(f"Input: {usage['input_tokens']}; output: {usage['output_tokens']}")


if __name__ == "__main__":
    main()
