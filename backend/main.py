from __future__ import annotations

import json
import math
import os
import re
import sqlite3
import uuid
from collections import Counter
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover
    PdfReader = None

app = FastAPI(title="AI Second Brain API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = Path(os.getenv("SECOND_BRAIN_DATA_DIR", "./data"))
UPLOAD_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "brain.db"
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "are", "was", "were", "you", "your",
    "一个", "我们", "他们", "以及", "可以", "进行", "通过", "因为", "所以", "如果", "这个", "那个",
}


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                source_type TEXT NOT NULL,
                file_name TEXT,
                content TEXT NOT NULL,
                summary TEXT,
                keywords TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                vector TEXT NOT NULL,
                FOREIGN KEY(document_id) REFERENCES documents(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cards (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                concept TEXT NOT NULL,
                explanation TEXT NOT NULL,
                review_question TEXT,
                related TEXT,
                FOREIGN KEY(document_id) REFERENCES documents(id)
            )
            """
        )
        conn.commit()


@app.on_event("startup")
def startup() -> None:
    init_db()


class TextIngestRequest(BaseModel):
    title: str = Field(min_length=1)
    text: str = Field(min_length=10)
    tags: list[str] = []


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)
    top_k: int = 5


def words(text: str) -> list[str]:
    return [w.lower() for w in re.findall(r"[\w\u4e00-\u9fff]+", text) if len(w) > 1 and w.lower() not in STOPWORDS]


def keywords(text: str, limit: int = 8) -> list[str]:
    counts = Counter(words(text))
    return [w for w, _ in counts.most_common(limit)]


def summarize(text: str, limit: int = 280) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    if len(clean) <= limit:
        return clean
    return clean[:limit].rstrip() + "..."


def chunk_text(text: str, size: int = 900, overlap: int = 120) -> list[str]:
    clean = re.sub(r"\s+", " ", text).strip()
    if not clean:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(clean):
        chunks.append(clean[start:start + size])
        start += size - overlap
    return chunks


def vectorize(text: str, dim: int = 128) -> list[float]:
    vec = [0.0] * dim
    for w in words(text):
        idx = hash(w) % dim
        vec[idx] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def parse_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        if PdfReader is None:
            raise HTTPException(status_code=400, detail="PDF support requires pypdf")
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return path.read_text(encoding="utf-8", errors="ignore")


def make_cards(document_id: str, text: str) -> list[dict[str, Any]]:
    kws = keywords(text, 6)
    cards = []
    for kw in kws[:4]:
        sentence = next((s.strip() for s in re.split(r"[。.!?\n]", text) if kw in s), "")
        cards.append({
            "id": str(uuid.uuid4()),
            "document_id": document_id,
            "concept": kw,
            "explanation": sentence[:220] or f"{kw} 是这份资料中的高频概念，需要结合原文继续复习。",
            "review_question": f"请用自己的话解释：{kw} 是什么？",
            "related": json.dumps([k for k in kws if k != kw][:3], ensure_ascii=False),
        })
    return cards


def ingest(title: str, content: str, source_type: str, file_name: str | None = None) -> str:
    if len(content.strip()) < 10:
        raise HTTPException(status_code=400, detail="Content is too short")
    document_id = str(uuid.uuid4())
    doc_keywords = keywords(content)
    doc_summary = summarize(content)
    chunks = chunk_text(content)
    cards = make_cards(document_id, content)
    with db() as conn:
        conn.execute(
            "INSERT INTO documents(id,title,source_type,file_name,content,summary,keywords) VALUES(?,?,?,?,?,?,?)",
            (document_id, title, source_type, file_name, content, doc_summary, json.dumps(doc_keywords, ensure_ascii=False)),
        )
        for i, chunk in enumerate(chunks):
            conn.execute(
                "INSERT INTO chunks(id,document_id,chunk_index,content,vector) VALUES(?,?,?,?,?)",
                (str(uuid.uuid4()), document_id, i, chunk, json.dumps(vectorize(chunk))),
            )
        for card in cards:
            conn.execute(
                "INSERT INTO cards(id,document_id,concept,explanation,review_question,related) VALUES(?,?,?,?,?,?)",
                (card["id"], card["document_id"], card["concept"], card["explanation"], card["review_question"], card["related"]),
            )
        conn.commit()
    return document_id


def retrieve(question: str, top_k: int = 5) -> list[dict[str, Any]]:
    qv = vectorize(question)
    with db() as conn:
        rows = conn.execute("SELECT chunks.*, documents.title FROM chunks JOIN documents ON documents.id = chunks.document_id").fetchall()
    scored = []
    for row in rows:
        score = cosine(qv, json.loads(row["vector"]))
        scored.append({
            "document_id": row["document_id"],
            "title": row["title"],
            "chunk_index": row["chunk_index"],
            "preview": row["content"][:360],
            "content": row["content"],
            "score": round(score, 4),
        })
    return sorted(scored, key=lambda x: x["score"], reverse=True)[:top_k]


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "AI Second Brain API Running", "docs": "/docs"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/documents/text")
def create_text_document(payload: TextIngestRequest) -> dict[str, str]:
    return {"id": ingest(payload.title, payload.text, "text")}


@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...), tags: str = Form(default="")) -> dict[str, str]:
    safe_name = Path(file.filename or "upload.txt").name.replace("/", "_").replace("\\", "_")
    target = UPLOAD_DIR / safe_name
    target.write_bytes(await file.read())
    text = parse_file(target)
    return {"id": ingest(target.stem, text, "upload", safe_name)}


@app.get("/api/documents")
def list_documents() -> list[dict[str, Any]]:
    with db() as conn:
        rows = conn.execute("SELECT id,title,source_type,file_name,summary,keywords,created_at FROM documents ORDER BY created_at DESC").fetchall()
    return [{**dict(r), "keywords": json.loads(r["keywords"] or "[]")} for r in rows]


@app.post("/api/chat")
def chat(payload: ChatRequest) -> dict[str, Any]:
    sources = retrieve(payload.question, payload.top_k)
    if not sources or sources[0]["score"] <= 0:
        return {"answer": "我还没有在你的知识库里找到足够相关的内容。可以先上传或粘贴更多资料。", "sources": []}
    bullets = "\n".join(f"- {s['preview']}" for s in sources[:3])
    answer = f"基于你的知识库，我检索到了以下相关内容：\n{bullets}\n\n综合来看，问题「{payload.question}」可以从这些资料中继续展开。建议优先阅读引用来源中得分最高的片段，并把其中的概念整理成知识卡片。"
    return {"answer": answer, "sources": sources}


@app.get("/api/cards")
def list_cards() -> list[dict[str, Any]]:
    with db() as conn:
        rows = conn.execute("SELECT * FROM cards ORDER BY rowid DESC").fetchall()
    return [{**dict(r), "related": json.loads(r["related"] or "[]")} for r in rows]


@app.post("/api/review")
def review() -> dict[str, Any]:
    docs = list_documents()
    cards = list_cards()
    all_keywords: list[str] = []
    for doc in docs:
        all_keywords.extend(doc.get("keywords", []))
    top = [w for w, _ in Counter(all_keywords).most_common(8)]
    return {
        "summary": f"当前知识库共有 {len(docs)} 份文档和 {len(cards)} 张知识卡片。你的近期学习重点集中在：{', '.join(top[:5]) or '暂无'}。",
        "high_frequency_topics": top,
        "blind_spots": ["把高频概念之间的关系补充成结构图", "为每个核心概念补充一个例子", "定期回顾低分引用片段"],
        "next_actions": ["继续上传相关资料", "围绕高频主题提问", "把回答整理成新的笔记"],
        "review_questions": [f"请解释 {c['concept']} 的含义和应用场景" for c in cards[:5]],
    }


@app.get("/api/graph")
def graph() -> dict[str, Any]:
    cards = list_cards()
    nodes = [{"id": c["concept"], "label": c["concept"]} for c in cards]
    edges = []
    for c in cards:
        for r in c.get("related", []):
            edges.append({"source": c["concept"], "target": r})
    return {"nodes": nodes, "edges": edges}
