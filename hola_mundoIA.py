import os
from google import genai
from dotenv import load_dotenv

# Cargamos las variables del .env para acceder a la clave de API
load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key = gemini_api_key)

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="What is AI in 1 line?"
)

print(response.text)