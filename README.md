# AI Second Brain

AI Second Brain 是一个 AI 驱动的个人智能知识库 Agent，用于自动整理、检索和复盘用户的长期知识内容。

## 核心能力

- 上传 PDF / Markdown / TXT 文档
- 自动生成摘要、关键词、核心观点和知识卡片
- 基于 RAG 的个人知识库问答
- 支持引用来源，减少脱离资料的幻觉回答
- Reflection Agent 自动生成学习总结、知识盲区和下一步建议
- 本地 SQLite 存储，适合快速 Demo 和二次开发

## Agent 工作流

1. Ingestion Agent：解析文档、清洗文本、切分知识块
2. Summary Agent：生成摘要、关键词、复习问题和知识卡片
3. Retrieval Agent：将知识块向量化并进行语义检索
4. Reasoning Agent：结合召回内容进行上下文问答
5. Memory Agent：记录高频主题、用户关注点和历史学习方向
6. Reflection Agent：生成周期性复盘、知识盲区和学习路径建议

## 技术栈

### Backend

- Python
- FastAPI
- SQLite
- 本地向量检索 fallback
- OpenAI API 可选

### Frontend

- Next.js
- React
- Tailwind CSS

## 快速启动

### 后端

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Windows PowerShell：

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

打开：

```text
http://localhost:3000
```

## 环境变量

后端可以选择配置 OpenAI API Key：

```bash
export OPENAI_API_KEY=your_api_key
```

没有 API Key 时，系统会使用本地 fallback 逻辑，仍然可以完成上传、检索和 Demo 流程。

## 项目亮点

这个项目不是简单 ChatBot，而是一个围绕个人知识长期积累构建的 Agentic Workflow。系统通过 RAG、长期记忆、多 Agent 协作和 Reflection Loop，让 AI 从被动问答工具变成主动知识管理助手。
