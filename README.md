# AI Wiki Quiz Generator

Full-stack app that scrapes a Wikipedia article, sends the cleaned text + section headings to Gemini, and returns a structured quiz (5–10 MCQs) with answers, explanations, difficulty, related topics, and key entities. FastAPI backend with Postgres, React frontend with two tabs (Generate & History), plus a take-quiz mode.

## Features
- Scrape Wikipedia HTML (no API) via BeautifulSoup; captures section headings.
- Gemini prompt (JSON mode) produces summary, key entities, sections, related topics, and quiz items (4 options, explanation, difficulty).
- FastAPI endpoints: generate quiz, list history, fetch quiz details.
- Postgres persistence of scraped text + quiz JSON.
- React UI with tabs, history table + details modal, take-quiz scoring (answers hidden until submit).
- Sample outputs in `sample_data/` for quick review.

## Quickstart
1. **Backend env**
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Env vars** (add to `backend/.env`, already gitignored)
   ```
   DATABASE_URL=postgresql://user:pass@localhost:5432/quizdb
   GEMINI_API_KEY=your_key_here
   ```
   Rotate any exposed keys immediately if this repo was shared.
3. **Run backend**
   ```bash
   uvicorn backend.main:app --reload --port 8000
   ```
4. **Frontend**
   ```bash
   cd ../frontend
   npm install
   npm run dev -- --host
   ```
   Default API base is `http://localhost:8000`; override with `VITE_API_BASE` in a `.env` file if needed.

## API
- `POST /generate_quiz` `{ url }` → full quiz payload.
- `GET /history` → list of past quizzes (id, url, title, summary, date).
- `GET /quiz/{id}` → full quiz payload for a stored quiz.

Response shape (abridged):
```json
{
  "id": 1,
  "url": "https://en.wikipedia.org/wiki/Alan_Turing",
  "title": "Alan Turing",
  "summary": "...",
  "key_entities": {"people": [], "organizations": [], "locations": []},
  "sections": ["Early life", "Legacy"],
  "related_topics": ["Enigma machine"],
  "quiz": [
    {
      "question": "...",
      "options": ["A","B","C","D"],
      "answer": "A",
      "explanation": "...",
      "difficulty": "medium"
    }
  ],
  "date_generated": "2026-01-08T00:00:00Z"
}
```

## Prompt template (Gemini)
Defined in [backend/llm_quiz_generator.py](backend/llm_quiz_generator.py) as `QUIZ_PROMPT_TEMPLATE` (JSON-mode). It instructs Gemini to ground answers in article text, output 5–10 MCQs with 4 options, explanations, difficulty, related topics, key entities, and to avoid hallucination. This fulfills the submission requirement for sharing the prompt template.

## Sample data
See `sample_data/` for example outputs:
- [sample_data/alan_turing.json](sample_data/alan_turing.json)
- [sample_data/python_language.json](sample_data/python_language.json)
- Mappings listed in [sample_data/urls.txt](sample_data/urls.txt)

## Notes and recommendations
- Ensure Postgres is running and accessible by `DATABASE_URL`. For MySQL, adjust the URL and driver accordingly.
- CORS is open to common Vite dev hosts; tighten for production.
- The scraper caps text length (~20k chars) to keep LLM costs bounded.
- Answers stay hidden until submission (take-quiz mode). You can retake or regenerate a quiz for the same article.
- After generation, refresh history in Tab 2 to see the latest entry.

## Testing (suggested)
- Unit-test scraper with mocked HTML.
- Mock Gemini client to validate prompt/JSON parsing.
- Integration-test `/generate_quiz` with a fake LLM response to ensure DB persistence and response schema.

## Screenshots
Capture after running locally: Tab 1 (Generate), Tab 2 (History table), and the Details modal.
