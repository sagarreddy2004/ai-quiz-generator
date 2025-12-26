"""LLM quiz generator using Google Generative AI.

This module first attempts to use the official Google Generative AI Python SDK
if available (package `google-generativeai` exposing `google.generativeai`).
If the SDK isn't present it falls back to the REST endpoint using `requests`.

The generate_quiz function returns a dict validated by Pydantic `QuizOutput`.
"""

import os
import json
from typing import Any
from dotenv import load_dotenv
import requests
from pydantic import BaseModel, Field, ValidationError

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


# Pydantic model for strict JSON
class QuizOutput(BaseModel):
    title: str = Field(..., description="Title of the Wikipedia article")
    summary: str = Field(..., description="Short summary of article")
    questions: list[dict] = Field(..., description="List of quiz questions")


_PROMPT_TEMPLATE = '''You are an AI that transforms Wikipedia articles into structured quiz data.

ARTICLE TEXT:
{article}

Generate a structured JSON object with the following fields:

- "title": title of the article
- "summary": 3–5 sentence summary
- "questions": a list of 5–10 quiz questions, each question must be a dict with:
    - "question"
    - "options" (list of 3–5 choices)
    - "answer"

Return ONLY valid JSON.
'''


def _extract_text_from_response(resp: Any) -> str:
    """Try several response shapes to extract the generated text."""
    if resp is None:
        return ""
    # If SDK returns a dict-like
    if isinstance(resp, dict):
        candidates = resp.get("candidates") or resp.get("outputs")
        if candidates and isinstance(candidates, list) and len(candidates) > 0:
            """LLM quiz generator using Google Generative AI.

            This module first attempts to use the official Google Generative AI Python SDK
            if available (package `google-generativeai` exposing `google.generativeai`).
            If the SDK isn't present it falls back to the REST endpoint using `requests`.

            The generate_quiz function returns a dict validated by Pydantic `QuizOutput`.
            """

            import os
            import json
            from typing import Any
            from dotenv import load_dotenv
            import requests
            from pydantic import BaseModel, Field, ValidationError

            load_dotenv()

            GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


            # Pydantic model for strict JSON
            class QuizOutput(BaseModel):
                title: str = Field(..., description="Title of the Wikipedia article")
                summary: str = Field(..., description="Short summary of article")
                questions: list[dict] = Field(..., description="List of quiz questions")


            _PROMPT_TEMPLATE = '''You are an AI that transforms Wikipedia articles into structured quiz data.

            ARTICLE TEXT:
            {article}

            Generate a structured JSON object with the following fields:

            - "title": title of the article
            - "summary": 3–5 sentence summary
            - "questions": a list of 5–10 quiz questions, each question must be a dict with:
                - "question"
                - "options" (list of 3–5 choices)
                - "answer"

            Return ONLY valid JSON.
            '''


            def _extract_text_from_response(resp: Any) -> str:
                """Try several response shapes to extract the generated text."""
                if resp is None:
                    return ""
                # If SDK returns a dict-like
                if isinstance(resp, dict):
                    candidates = resp.get("candidates") or resp.get("outputs")
                    if candidates and isinstance(candidates, list) and len(candidates) > 0:
                        first = candidates[0]
                        if isinstance(first, dict):
                            for k in ("output", "text", "content"):
                                if k in first:
                                    v = first[k]
                                    if isinstance(v, str):
                                        return v
                                    if isinstance(v, list):
                                        for item in v:
                                            if isinstance(item, dict) and item.get("type") in ("output_text", "text"):
                                                return item.get("text", "")
                            return json.dumps(first)
                    for k in ("output", "text", "generated_text"):
                        if k in resp and isinstance(resp[k], str):
                            return resp[k]
                    if isinstance(resp.get("candidates"), list) and isinstance(resp["candidates"][0], str):
                        return resp["candidates"][0]
                    return json.dumps(resp)

                if hasattr(resp, "candidates"):
                    try:
                        return _extract_text_from_response(resp.candidates)
                    except Exception:
                        pass

                try:
                    return str(resp)
                except Exception:
                    return ""


            def _call_google_sdk(prompt_text: str, model: str = "models/gemini-1.0") -> str:
                """Try to use the installed google.generativeai SDK if available.

                Returns the raw generated string.
                """
                try:
                    import google.generativeai as genai
                except Exception:
                    raise RuntimeError("Google Generative AI SDK not installed")

                if not GEMINI_API_KEY:
                    raise RuntimeError("GEMINI_API_KEY not set in environment")

                try:
                    if hasattr(genai, "configure"):
                        genai.configure(api_key=GEMINI_API_KEY)
                except Exception:
                    pass

                try:
                    if hasattr(genai, "generate_text"):
                        resp = genai.generate_text(model=model, prompt=prompt_text)
                        if not isinstance(resp, dict) and hasattr(resp, "to_dict"):
                            resp = resp.to_dict()
                        return _extract_text_from_response(resp)

                    if hasattr(genai, "generate"):
                        resp = genai.generate(model=model, prompt=prompt_text)
                        return _extract_text_from_response(resp)

                    if hasattr(genai, "predict"):
                        resp = genai.predict(model=model, prompt=prompt_text)
                        return _extract_text_from_response(resp)

                except Exception as e:
                    raise RuntimeError(f"SDK call failed: {e}")

                raise RuntimeError("No supported SDK method found on google.generativeai package")


            def _call_google_rest(prompt_text: str, model: str = "models/gemini-1.0") -> str:
                """Call the Generative Language REST endpoint using requests and API key.

                This avoids depending on an SDK. Returns the generated text.
                """
                if not GEMINI_API_KEY:
                    raise RuntimeError("GEMINI_API_KEY not set in environment")

                base = "https://generativelanguage.googleapis.com/v1beta2"
                url = f"{base}/{model}:generate?key={GEMINI_API_KEY}" if not model.startswith("http") else f"{model}?key={GEMINI_API_KEY}"

                payload = {
                    "prompt": {"text": prompt_text},
                    "temperature": 0.0,
                    "max_output_tokens": 1600,
                }

                resp = requests.post(url, json=payload, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                return _extract_text_from_response(data)


            def generate_quiz(article_text: str) -> dict:
                """Generate a quiz dict from article_text.

                Tries SDK first (if installed), falls back to REST.
                Expects the model to return valid JSON text which will then be parsed and validated by Pydantic.
                """
                prompt_text = _PROMPT_TEMPLATE.format(article=article_text)

                last_err = None
                for caller in (_call_google_sdk, _call_google_rest):
                    try:
                        raw = caller(prompt_text)
                        try:
                            parsed = json.loads(raw)
                        except Exception:
                            start = raw.find("{")
                            end = raw.rfind("}")
                            if start != -1 and end != -1 and end > start:
                                try:
                                    parsed = json.loads(raw[start:end+1])
                                except Exception:
                                    raise RuntimeError("LLM output not valid JSON")
                            else:
                                raise RuntimeError("LLM output not valid JSON")

                        try:
                            q = QuizOutput.parse_obj(parsed)
                            return q.dict()
                        except ValidationError as ve:
                            raise RuntimeError(f"LLM output failed validation: {ve}")

                    except Exception as e:
                        last_err = e
                        continue

                raise RuntimeError(f"All LLM callers failed. Last error: {last_err}")


            if __name__ == "__main__":
                sample = "Python is a programming language created by Guido van Rossum."
                print("Testing LLM generator (no network calls in import)...")
                try:
                    print("module loaded OK")
                except Exception as e:
                    print("Error during local test:", e)

    # if it's a pydantic model instance, call .dict(); otherwise return as-is
    if hasattr(parsed, "dict") and callable(parsed.dict):
        return parsed.dict()
    elif isinstance(parsed, dict):
        return parsed
    else:
        # last-resort: try to coerce to dict (e.g., if it's a simple Namespace-like)
        try:
            return dict(parsed)
        except Exception:
            raise RuntimeError("Unable to parse LLM output into a dict. Got: " + repr(parsed))
    """
    Takes article text and returns validated JSON quiz dict.
    """
    prompt_text = quiz_prompt.format(article=article_text)
import os
import json
from typing import Any
from dotenv import load_dotenv
import requests
from pydantic import BaseModel, Field, ValidationError

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Pydantic model for strict JSON
class QuizOutput(BaseModel):
    title: str = Field(..., description="Title of the Wikipedia article")
    summary: str = Field(..., description="Short summary of article")
    questions: list[dict] = Field(..., description="List of quiz questions")


_PROMPT_TEMPLATE = '''You are an AI that transforms Wikipedia articles into structured quiz data.

ARTICLE TEXT:
{article}

Generate a structured JSON object with the following fields:

- "title": title of the article
- "summary": 3–5 sentence summary
- "questions": a list of 5–10 quiz questions, each question must be a dict with:
    - "question"
    - "options" (list of 3–5 choices)
    - "answer"

Return ONLY valid JSON.
'''


def _extract_text_from_response(resp: Any) -> str:
    """Try several response shapes to extract the generated text."""
    if resp is None:
        return ""
    # If SDK returns a dict-like
    if isinstance(resp, dict):
        # common shapes: {'candidates': [{'output': '...'}]}, or {'candidates':[{'content':[{'type':'output_text','text':'...'}]}]}
        candidates = resp.get("candidates") or resp.get("outputs")
        if candidates and isinstance(candidates, list) and len(candidates) > 0:
            first = candidates[0]
            if isinstance(first, dict):
                # try several keys
                for k in ("output", "text", "content"):
                    if k in first:
                        v = first[k]
                        if isinstance(v, str):
                            return v
                        if isinstance(v, list):
                            # content list
                            for item in v:
                                if isinstance(item, dict) and item.get("type") in ("output_text", "text"):
                                    return item.get("text", "")
                # fallback: stringify
                return json.dumps(first)
        # final fallback: try top-level 'output' or 'text'
        for k in ("output", "text", "generated_text"):
            if k in resp and isinstance(resp[k], str):
                return resp[k]
        # if there's a top-level 'candidates' that are strings
        if isinstance(resp.get("candidates"), list) and isinstance(resp["candidates"][0], str):
            return resp["candidates"][0]
        # nothing matched
        return json.dumps(resp)

    # if it's an object with attributes
    if hasattr(resp, "candidates"):
        try:
            return _extract_text_from_response(resp.candidates)
        except Exception:
            pass

    # last resort
    try:
        return str(resp)
    except Exception:
        return ""


def _call_google_sdk(prompt_text: str, model: str = "models/gemini-1.0") -> str:
    """Try to use the installed google.generativeai SDK if available.

    Returns the raw generated string.
    """
    try:
        # import here to avoid forcing SDK at module import time
        import google.generativeai as genai
    except Exception:
        raise RuntimeError("Google Generative AI SDK not installed")

    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not set in environment")

    # configure client (SDK uses genai.configure)
    try:
        # Some versions use genai.configure(api_key=...)
        if hasattr(genai, "configure"):
            genai.configure(api_key=GEMINI_API_KEY)
    except Exception:
        # ignore configuration errors here; SDK may use env var
        pass

    # SDK method may vary between versions; try common names
    try:
        # newer SDK: genai.generate_text(model=model, prompt=...)
        if hasattr(genai, "generate_text"):
            resp = genai.generate_text(model=model, prompt=prompt_text)
            return _extract_text_from_response(resp if isinstance(resp, dict) else getattr(resp, "to_dict", lambda: resp)())

        # alternate: genai.generate or genai.predict
        if hasattr(genai, "generate"):
            resp = genai.generate(model=model, prompt=prompt_text)
            return _extract_text_from_response(resp)

        if hasattr(genai, "predict"):
            resp = genai.predict(model=model, prompt=prompt_text)
            return _extract_text_from_response(resp)

    except Exception as e:
        raise RuntimeError(f"SDK call failed: {e}")

    raise RuntimeError("No supported SDK method found on google.generativeai package")


def _call_google_rest(prompt_text: str, model: str = "models/gemini-1.0") -> str:
    """Call the Generative Language REST endpoint using requests and API key.

    This avoids depending on an SDK. Returns the generated text.
    """
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not set in environment")

    # Construct endpoint URL. This path may vary by API version; v1beta2 is common.
    base = "https://generativelanguage.googleapis.com/v1beta2"
    url = f"{base}/{model}:generate?key={GEMINI_API_KEY}" if not model.startswith("http") else f"{model}?key={GEMINI_API_KEY}"

    payload = {
        "prompt": {"text": prompt_text},
        "temperature": 0.0,
        "max_output_tokens": 1600,
    }

    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return _extract_text_from_response(data)


def generate_quiz(article_text: str) -> dict:
    """Generate a quiz dict from article_text.

    Tries SDK first (if installed), falls back to REST.
    Expects the model to return valid JSON text which will then be parsed and validated by Pydantic.
    """
    prompt_text = _PROMPT_TEMPLATE.format(article=article_text)

    # Try SDK first
    last_err = None
    for caller in (_call_google_sdk, _call_google_rest):
        try:
            raw = caller(prompt_text)
            # attempt to load JSON from raw text
            try:
                parsed = json.loads(raw)
            except Exception:
                # If raw contains extra text, try to extract JSON substring
                start = raw.find("{")
                end = raw.rfind("}")
                if start != -1 and end != -1 and end > start:
                    try:
                        parsed = json.loads(raw[start:end+1])
                    except Exception:
                        raise RuntimeError("LLM output not valid JSON")
                else:
                    raise RuntimeError("LLM output not valid JSON")

            # validate with Pydantic
            try:
                q = QuizOutput.parse_obj(parsed)
                return q.dict()
            except ValidationError as ve:
                raise RuntimeError(f"LLM output failed validation: {ve}")

        except Exception as e:
            last_err = e
            # try next caller
            continue

    raise RuntimeError(f"All LLM callers failed. Last error: {last_err}")


if __name__ == "__main__":
    sample = "Python is a programming language created by Guido van Rossum."
    print("Testing LLM generator (no network calls in import)...")
    try:
        print("module loaded OK")
    except Exception as e:
        print("Error during local test:", e)

