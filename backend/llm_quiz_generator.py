import json
import os
import traceback
from string import Template
from textwrap import dedent

from dotenv import load_dotenv
from google import genai  # Requires `pip install google-genai`
from google.genai import types

load_dotenv()

# Setup Gemini Client
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY not set in .env file")

client = genai.Client(api_key=GEMINI_API_KEY)

# Model tuned for speed and structured JSON
MODEL_ID = "gemini-2.5-flash-lite"

# Prompt template (also documented in README for submission requirements).
# Use string.Template to avoid brace-escaping issues when injecting variables.
QUIZ_PROMPT_TEMPLATE = Template(
        dedent(
                """
                You are a careful quiz generator that must stay grounded in the provided Wikipedia article text.
                Produce 5 to 10 multiple-choice questions (4 options each) with answers and short explanations.

                Input metadata:
                - Article title: $title
                - Article sections (from HTML headings):
                $sections

                Use only facts present in the article excerpt below. If something is unclear, omit it instead of guessing.

                Return STRICT JSON (no markdown) with this shape:
                {
                    "title": "<article title>",
                    "summary": "1-3 sentence overview grounded in the article",
                    "key_entities": {
                        "people": ["..."],
                        "organizations": ["..."],
                        "locations": ["..."]
                    },
                    "sections": ["<section heading from article>"],
                    "related_topics": ["<3-8 Wikipedia topics for further reading>"],
                    "quiz": [
                        {
                            "question": "...",
                            "options": ["A", "B", "C", "D"],
                            "answer": "must exactly match one option",
                            "explanation": "1-2 sentence fact-based justification",
                            "difficulty": "easy|medium|hard"
                        }
                    ]
                }

                Rules:
                - 5 to 10 questions only.
                - Each question must have exactly 4 distinct options; answer must be one of them.
                - Keep explanations concise and factual.
                - Use the section list provided; do not invent non-existent sections.
                - Do not include any text outside the JSON object.

                Article excerpt (truncated if long):
                $article_excerpt
                """
        )
)


def _extract_text_from_response(response) -> str:
    """Best-effort extraction of JSON text from the Gemini response object."""
    if hasattr(response, "text") and response.text:
        return response.text

    # Fallback: concatenate candidate parts
    try:
        texts = []
        for cand in getattr(response, "candidates", []) or []:
            content = getattr(cand, "content", None)
            if not content:
                continue
            for part in getattr(content, "parts", []) or []:
                text_part = getattr(part, "text", None)
                if text_part:
                    texts.append(text_part)
        return "\n".join(texts).strip()
    except Exception:
        return ""


def _cleanup_json_text(raw_text: str) -> str:
    """Strip code fences and isolate the first JSON object/array for robust parsing."""
    if not raw_text:
        return ""

    text = raw_text.strip()

    # Remove markdown fences if present
    if text.startswith("```"):
        text = text.split("```", 2)[1] if "```" in text[3:] else text
        text = text.replace("json", "", 1).strip() if text.startswith("json") else text.strip()

    # Heuristic: grab from first '{' or '[' to last matching brace/bracket
    start_obj = text.find("{")
    start_arr = text.find("[")
    start_idx_candidates = [i for i in [start_obj, start_arr] if i != -1]
    if not start_idx_candidates:
        return text
    start_idx = min(start_idx_candidates)
    end_idx = max(text.rfind("}"), text.rfind("]"))
    if end_idx != -1 and end_idx > start_idx:
        text = text[start_idx : end_idx + 1]
    return text.strip()


def generate_quiz(article_text: str, *, title: str = "", sections: list[str] | None = None) -> dict:
    """Generate a structured quiz JSON from article text using Gemini."""
    section_block = "\n".join(f"- {s}" for s in (sections or []) if s)
    prompt = QUIZ_PROMPT_TEMPLATE.substitute(
        title=title or "Wikipedia article",
        sections=section_block or "(no section headings detected)",
        article_excerpt=article_text[:9000],
    )

    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=None,
                response_mime_type="application/json",
                temperature=0.35,
                max_output_tokens=2200,
            ),
        )
    except Exception as exc:
        trace = traceback.format_exc()
        raise RuntimeError(f"Model call failed: {exc} | trace={trace}")

    raw_text = _extract_text_from_response(response)
    cleaned = _cleanup_json_text(raw_text)

    # Debug previews to help diagnose malformed outputs during development
    preview_raw = (raw_text or "")[:400].replace("\n", " ")
    preview_clean = (cleaned or "")[:400].replace("\n", " ")
    print(f"[LLM RAW PREVIEW] {preview_raw}")
    print(f"[LLM CLEAN PREVIEW] {preview_clean}")

    if not cleaned:
        raise RuntimeError("Model returned empty response")

    # If the model omitted outer braces (e.g., starts with "title"), wrap it
    if cleaned and not cleaned.lstrip().startswith("{") and not cleaned.lstrip().startswith("["):
        cleaned = "{" + cleaned.strip().lstrip(",")
        if not cleaned.endswith("}"):
            cleaned += "}"

    try:
        quiz_data = json.loads(cleaned)
    except json.JSONDecodeError as exc:  # defensive path
        preview = cleaned[:400].replace("\n", " ")
        raise RuntimeError(f"Model failed to return valid JSON: {exc} | preview={preview!r}")

    # If the model double-encoded the JSON (string containing JSON), decode again
    if isinstance(quiz_data, str):
        nested_clean = _cleanup_json_text(quiz_data)
        try:
            quiz_data = json.loads(nested_clean)
        except Exception as exc:
            preview = nested_clean[:400].replace("\n", " ")
            raise RuntimeError(f"Model returned a string instead of JSON; could not parse nested JSON: {exc} | preview={preview!r}")

    if not isinstance(quiz_data, dict):
        raise RuntimeError("Model output must be a JSON object")

    # Light schema checks to fail fast before DB/storage
    quiz_items = quiz_data.get("quiz") or quiz_data.get("questions") or []
    if not (5 <= len(quiz_items) <= 10):
        raise RuntimeError("Model must return between 5 and 10 questions")
    for i, item in enumerate(quiz_items):
        if not isinstance(item, dict):
            raise RuntimeError(f"Question {i+1} must be an object")
        opts = item.get("options", []) if isinstance(item, dict) else []
        if len(opts) != 4:
            raise RuntimeError(f"Question {i+1} must have exactly 4 options")
        ans = item.get("answer") if isinstance(item, dict) else None
        if ans not in opts:
            raise RuntimeError(f"Question {i+1} answer must match one option")

    # Standardize field name to "quiz" while preserving any provided title
    quiz_data["title"] = quiz_data.get("title") or title or "Wikipedia Quiz"
    quiz_data["quiz"] = quiz_items
    return quiz_data


if __name__ == "__main__":  # pragma: no cover - manual test only
    sample = "The Eiffel Tower is a wrought-iron lattice tower on the Champ de Mars in Paris..."
    quiz = generate_quiz(sample, title="Eiffel Tower", sections=["History", "Design"])
    print(f"Generated {len(quiz['quiz'])} questions.")
    print(json.dumps(quiz, indent=2))