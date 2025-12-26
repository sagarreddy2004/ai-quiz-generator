# backend/main.py
import json
from datetime import datetime
from typing import List

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from database import SessionLocal, create_tables, Quiz
from scraper import scrape_wikipedia
from llm_quiz_generator import generate_quiz

# Ensure tables exist
create_tables()

app = FastAPI(title="AI Wiki Quiz Generator")

# Allow local frontend during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        # Vite preview frequently uses port 4173 — allow it during local testing
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],

    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Pydantic schemas for API ---------- #
class QuestionSchema(BaseModel):
    question: str
    options: List[str]
    answer: str

class QuizOutputSchema(BaseModel):
    id: int
    url: str
    title: str | None
    date_generated: datetime
    summary: str | None
    questions: List[QuestionSchema]

class GenerateRequest(BaseModel):
    url: str

class HistoryItem(BaseModel):
    id: int
    url: str
    title: str | None
    date_generated: datetime

# ---------- DB dependency ---------- #
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------- Endpoints ---------- #
@app.post("/generate_quiz", response_model=QuizOutputSchema)
def generate_quiz_endpoint(req: GenerateRequest, db=Depends(get_db)):
    # 1) scrape the article
    try:
        title, article_text = scrape_wikipedia(req.url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Scraping failed: {e}")

    # 2) generate quiz via LLM
    try:
        quiz_json = generate_quiz(article_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM generation failed: {e}")

    # 3) prepare data for DB
    full_quiz_text = json.dumps(quiz_json, ensure_ascii=False)
    # store the title returned by scraper (fallback to quiz_json title)
    db_title = title or quiz_json.get("title")

    q = Quiz(
        url=req.url,
        title=db_title,
        scraped_content=article_text,
        full_quiz_data=full_quiz_text,
    )
    db.add(q)
    db.commit()
    db.refresh(q)

    # 4) build response
    # Ensure fields exist in quiz_json
    response_obj = {
        "id": q.id,
        "url": q.url,
        "title": q.title,
        "date_generated": q.date_generated,
        "summary": quiz_json.get("summary"),
        "questions": quiz_json.get("questions", []),
    }
    return response_obj

@app.get("/history", response_model=List[HistoryItem])
def history(db=Depends(get_db)):
    rows = db.query(Quiz).order_by(Quiz.date_generated.desc()).all()
    result = []
    for r in rows:
        result.append({
            "id": r.id,
            "url": r.url,
            "title": r.title,
            "date_generated": r.date_generated,
        })
    return result

@app.get("/quiz/{quiz_id}", response_model=QuizOutputSchema)
def get_quiz(quiz_id: int, db=Depends(get_db)):
    r = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Quiz not found")
    try:
        quiz_data = json.loads(r.full_quiz_data)
    except Exception:
        quiz_data = {"summary": None, "questions": []}

    return {
        "id": r.id,
        "url": r.url,
        "title": r.title,
        "date_generated": r.date_generated,
        "summary": quiz_data.get("summary"),
        "questions": quiz_data.get("questions", []),
    }
