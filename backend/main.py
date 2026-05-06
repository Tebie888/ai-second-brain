from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from typing import List
import sqlite3
import uuid

app = FastAPI(title='AI Second Brain')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

DB_PATH = 'brain.db'
UPLOAD_DIR = Path('uploads')
UPLOAD_DIR.mkdir(exist_ok=True)

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cur = conn.cursor()

cur.execute('''
CREATE TABLE IF NOT EXISTS notes (
    id TEXT PRIMARY KEY,
    title TEXT,
    content TEXT,
    summary TEXT
)
''')
conn.commit()

class NoteInput(BaseModel):
    title: str
    content: str

class AskInput(BaseModel):
    question: str

@app.get('/')
def root():
    return {'message': 'AI Second Brain API Running'}

@app.post('/notes')
def create_note(note: NoteInput):
    note_id = str(uuid.uuid4())

    summary = note.content[:200]

    cur.execute(
        'INSERT INTO notes VALUES (?, ?, ?, ?)',
        (note_id, note.title, note.content, summary)
    )
    conn.commit()

    return {
        'id': note_id,
        'summary': summary
    }

@app.get('/notes')
def list_notes():
    rows = cur.execute('SELECT id, title, summary FROM notes').fetchall()

    return [
        {
            'id': r[0],
            'title': r[1],
            'summary': r[2]
        }
        for r in rows
    ]

@app.post('/upload')
async def upload_file(file: UploadFile = File(...)):
    file_path = UPLOAD_DIR / file.filename

    with open(file_path, 'wb') as f:
        f.write(await file.read())

    content = file_path.read_text(errors='ignore')

    note_id = str(uuid.uuid4())

    summary = content[:300]

    cur.execute(
        'INSERT INTO notes VALUES (?, ?, ?, ?)',
        (note_id, file.filename, content, summary)
    )
    conn.commit()

    return {
        'message': 'uploaded',
        'id': note_id,
        'summary': summary
    }

@app.post('/ask')
def ask_question(data: AskInput):
    rows = cur.execute('SELECT title, content FROM notes').fetchall()

    matched = []

    for title, content in rows:
        if any(word.lower() in content.lower() for word in data.question.split()):
            matched.append({
                'title': title,
                'content': content[:500]
            })

    if not matched:
        return {
            'answer': 'No relevant knowledge found.',
            'sources': []
        }

    context = '\n'.join([m['content'] for m in matched[:3]])

    answer = f'Based on your knowledge base, here are related notes:\n\n{context[:1000]}'

    return {
        'answer': answer,
        'sources': [m['title'] for m in matched[:3]]
    }

@app.get('/reflection')
def reflection():
    rows = cur.execute('SELECT title FROM notes').fetchall()

    topics = [r[0] for r in rows]

    return {
        'total_notes': len(topics),
        'high_frequency_topics': topics[:5],
        'reflection': 'You are consistently learning and building long-term knowledge.',
        'next_step': 'Continue uploading documents and asking questions to strengthen your memory graph.'
    }
