import os
from dotenv import load_dotenv
from google import genai

# Load environment variables from .env
load_dotenv()

# Get API key
api_key = os.getenv("GEMINI_API_KEY")

# Create Gemini client
client = genai.Client(api_key=api_key)

chat = client.chats.create(model="gemini-2.5-flash")

print("Chatbot is ready! (Type 'quit' to exit)")

while True:
    user_input = input("\nYou: ")

    if user_input.lower() == "quit":
        break

    response = chat.send_message(user_input)
    print(f"Gemini: {response.text}")