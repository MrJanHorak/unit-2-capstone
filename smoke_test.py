from dotenv import load_dotenv
from google import genai

load_dotenv()

# The client automatically picks up the GEMINI_API_KEY environment variable
client = genai.Client()

response = client.models.generate_content(
    model="gemini-3.5-flash", 
    contents="Explain quantum computing in one sentence."
)

print(response.text)