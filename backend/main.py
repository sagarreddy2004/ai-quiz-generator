# backend/main.py
import json
from datetime import datetime
from typing import List

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, root_validator, validator

# Use package-qualified imports so running from the repo root works
from backend.database import Quiz, SessionLocal, create_tables
from backend.llm_quiz_generator import generate_quiz
import traceback
from backend.scraper import ScrapeResult, scrape_wikipedia

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
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Pydantic schemas ---------- #
class KeyEntities(BaseModel):
    people: List[str] = []
    organizations: List[str] = []
    locations: List[str] = []


class QuizItem(BaseModel):
    question: str
    options: List[str]
    answer: str
    explanation: str | None = None
    difficulty: str = Field(..., pattern=r"^(easy|medium|hard)$")

    @validator("options")
    def options_must_have_four(cls, v):
        if len(v) != 4:
            raise ValueError("Each question must have exactly 4 options")
        return v

    @validator("answer")
    def answer_must_match_option(cls, v, values):
        options = values.get("options", [])
        if options and v not in options:
            raise ValueError("Answer must be one of the options")
        return v
@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "AI Wiki Quiz Generator",
        "docs": "/docs"
    }


class GeneratedQuiz(BaseModel):
    title: str | None = None
    summary: str | None = None
    key_entities: KeyEntities = KeyEntities()
    sections: List[str] = []
    related_topics: List[str] = []
    quiz: List[QuizItem]

    @root_validator(pre=True)
    def accept_questions_alias(cls, values):
        if "quiz" not in values and "questions" in values:
            values["quiz"] = values.get("questions")
        return values

    @validator("quiz")
    def enforce_question_count(cls, v):
        if not (5 <= len(v) <= 10):
            raise ValueError("Quiz must contain 5 to 10 questions")
        return v

    class Config:
        extra = "ignore"


class QuizOutputSchema(BaseModel):
    id: int
    url: str
    title: str | None
    date_generated: datetime
    summary: str | None
    key_entities: KeyEntities
    sections: List[str]
    related_topics: List[str]
    quiz: List[QuizItem]


class GenerateRequest(BaseModel):
    url: str


class HistoryItem(BaseModel):
    id: int
    url: str
    title: str | None
    date_generated: datetime
    summary: str | None = None

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
    if "wikipedia.org" not in req.url:
        raise HTTPException(status_code=400, detail="Only Wikipedia article URLs are supported.")

    # 1) scrape the article
    try:
        scrape_result: ScrapeResult = scrape_wikipedia(req.url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Scraping failed: {e}")

    # 2) generate quiz via LLM
    try:
        quiz_json = generate_quiz(
            scrape_result.text,
            title=scrape_result.title,
            sections=scrape_result.sections,
        )
        generated = GeneratedQuiz.parse_obj(quiz_json)
    except Exception as e:
        print("[LLM ERROR]", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"LLM generation failed: {e}")

    # 3) save to DB
    # Pydantic v2: use model_dump_json to control encoding
    full_quiz_text = generated.model_dump_json(ensure_ascii=False)
    db_title = scrape_result.title or generated.title

    q = Quiz(
        url=req.url,
        title=db_title,
        scraped_content=scrape_result.text,
        full_quiz_data=full_quiz_text,
    )
    db.add(q)
    db.commit()
    db.refresh(q)

    return {
        "id": q.id,
        "url": q.url,
        "title": q.title,
        "date_generated": q.date_generated,
        "summary": generated.summary,
        "key_entities": generated.key_entities,
        "sections": generated.sections,
        "related_topics": generated.related_topics,
        "quiz": generated.quiz,
    }

@app.get("/history", response_model=List[HistoryItem])
def history(db=Depends(get_db)):
    rows = db.query(Quiz).order_by(Quiz.date_generated.desc()).all()
    history_rows = []
    for r in rows:
        try:
            payload = json.loads(r.full_quiz_data) if r.full_quiz_data else {}
            summary = payload.get("summary")
        except Exception:
            summary = None
        history_rows.append(
            {
                "id": r.id,
                "url": r.url,
                "title": r.title,
                "date_generated": r.date_generated,
                "summary": summary,
            }
        )
    return history_rows

@app.get("/quiz/{quiz_id}", response_model=QuizOutputSchema)
def get_quiz(quiz_id: int, db=Depends(get_db)):
    r = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Quiz not found")

    try:
        quiz_data = json.loads(r.full_quiz_data)
        generated = GeneratedQuiz.parse_obj(quiz_data)
    except Exception:
        raise HTTPException(status_code=500, detail="Stored quiz data is corrupted")

    return {
        "id": r.id,
        "url": r.url,
        "title": r.title,
        "date_generated": r.date_generated,
        "summary": generated.summary,
        "key_entities": generated.key_entities,
        "sections": generated.sections,
        "related_topics": generated.related_topics,
        "quiz": generated.quiz,
    }
