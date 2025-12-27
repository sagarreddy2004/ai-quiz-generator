import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# Setup Gemini Client
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY not set in .env file")

client = genai.Client(api_key=GEMINI_API_KEY)

# Use Gemini 2.5 Flash-Lite for high-volume free tier usage
MODEL_ID = "gemini-2.5-flash-lite" 

# UPDATED: Instructed for 10 questions
SYSTEM_PROMPT = """
You are a quiz generator. Generate a comprehensive quiz with exactly 10 multiple-choice questions based on the text.
Each question must have 4 options and one correct answer.
Return the data in the following JSON format:
{
  "summary": "short overview of the topic",
  "questions": [
    {
      "question": "...",
      "options": ["A", "B", "C", "D"],
      "answer": "correct option string"
    }
  ]
}
"""

def generate_quiz(article_text: str) -> dict:
    # Use a larger slice of text if needed for 10 questions
    prompt = f"Article Content:\n{article_text[:8000]}\n\nGenerate the 10-question quiz now."

    response = client.models.generate_content(
        model=MODEL_ID,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            temperature=0.4,
            # Increased max_output_tokens to fit 10 questions
            max_output_tokens=2000 
        )
    )

    try:
        quiz_data = json.loads(response.text)
        return {
            "title": "Gemini 10-Question Quiz",
            "summary": quiz_data.get("summary", ""),
            "questions": quiz_data.get("questions", [])
        }
    except json.JSONDecodeError:
        raise RuntimeError("Model failed to return valid JSON. Try reducing article length.")

# Example Usage
if __name__ == "__main__":
    sample_text = "Mount Everest is Earth's highest mountain..."
    quiz = generate_quiz(sample_text)
    
    # Print count to verify
    print(f"Total Questions Generated: {len(quiz['questions'])}")
    print(json.dumps(quiz, indent=2))