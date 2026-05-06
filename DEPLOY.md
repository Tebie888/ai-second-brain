# Deployment Guide

## Local Development

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open:

- Frontend: http://localhost:3000
- Backend Docs: http://localhost:8000/docs

---

## Docker

Run the entire stack:

```bash
docker-compose up --build
```

---

## Vercel + Railway

Recommended production deployment:

### Frontend
- Deploy `frontend/` to Vercel

### Backend
- Deploy `backend/` to Railway or Render

Set:

```env
NEXT_PUBLIC_API_BASE=https://your-api-domain.com
```

---

## Future Improvements

- OpenAI Embedding API
- pgvector / ChromaDB
- LangGraph multi-agent orchestration
- User authentication
- Notion sync
- Knowledge graph visualization
