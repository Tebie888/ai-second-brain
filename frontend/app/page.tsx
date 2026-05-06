"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

type DocumentItem = {
  id: string;
  title: string;
  source_type: string;
  summary: string;
  keywords: string[];
  created_at: string;
};

type CardItem = {
  id: string;
  concept: string;
  explanation: string;
  review_question: string;
  related: string[];
};

export default function HomePage() {
  const [title, setTitle] = useState("Transformer 学习笔记");
  const [text, setText] = useState(
    "Transformer 使用 self-attention 机制建模 token 之间的关系。相比 RNN，它更适合并行计算，也能通过多头注意力学习不同语义子空间。RAG 则通过检索外部知识来增强大模型回答的可信度。"
  );
  const [question, setQuestion] = useState("Transformer 和 RAG 有什么关系？");
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [cards, setCards] = useState<CardItem[]>([]);
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState<any[]>([]);
  const [review, setReview] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const stats = useMemo(
    () => [
      { label: "Documents", value: documents.length },
      { label: "Knowledge Cards", value: cards.length },
      { label: "Agent Steps", value: 6 },
    ],
    [documents.length, cards.length]
  );

  async function refresh() {
    const [docsRes, cardsRes] = await Promise.all([
      fetch(`${API_BASE}/api/documents`),
      fetch(`${API_BASE}/api/cards`),
    ]);
    if (docsRes.ok) setDocuments(await docsRes.json());
    if (cardsRes.ok) setCards(await cardsRes.json());
  }

  useEffect(() => {
    refresh().catch(() => {});
  }, []);

  async function addText(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      await fetch(`${API_BASE}/api/documents/text`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, text }),
      });
      await refresh();
    } finally {
      setLoading(false);
    }
  }

  async function uploadFile(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const input = e.currentTarget.elements.namedItem("file") as HTMLInputElement;
    if (!input?.files?.[0]) return;
    const form = new FormData();
    form.append("file", input.files[0]);
    setLoading(true);
    try {
      await fetch(`${API_BASE}/api/documents/upload`, { method: "POST", body: form });
      input.value = "";
      await refresh();
    } finally {
      setLoading(false);
    }
  }

  async function ask(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, top_k: 5 }),
      });
      const data = await res.json();
      setAnswer(data.answer);
      setSources(data.sources || []);
    } finally {
      setLoading(false);
    }
  }

  async function runReview() {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/review`, { method: "POST" });
      setReview(await res.json());
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="container">
      <section className="hero">
        <h1>AI Second Brain</h1>
        <p>
          一个 AI 驱动的个人知识库 Agent：自动摄取文档、生成知识卡片、执行 RAG 问答，并通过
          Reflection Agent 输出学习复盘和下一步建议。
        </p>
      </section>

      <section className="grid three">
        {stats.map((s) => (
          <div className="card" key={s.label}>
            <h3>{s.value}</h3>
            <p className="small">{s.label}</p>
          </div>
        ))}
      </section>

      <section className="grid two">
        <form className="card" onSubmit={addText}>
          <h2>Ingestion Agent</h2>
          <p className="small">粘贴笔记内容，系统会自动切片、摘要、抽取关键词并生成知识卡片。</p>
          <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="标题" />
          <br />
          <br />
          <textarea value={text} onChange={(e) => setText(e.target.value)} placeholder="输入笔记内容" />
          <br />
          <br />
          <button disabled={loading}>保存到知识库</button>
        </form>

        <form className="card" onSubmit={uploadFile}>
          <h2>File Upload</h2>
          <p className="small">支持 TXT / Markdown / PDF。PDF 文本提取依赖后端 pypdf。</p>
          <input name="file" type="file" accept=".txt,.md,.pdf" />
          <br />
          <br />
          <button className="secondary" disabled={loading}>上传文档</button>
        </form>
      </section>

      <section className="grid two">
        <form className="card" onSubmit={ask}>
          <h2>Retrieval + Reasoning Agent</h2>
          <textarea value={question} onChange={(e) => setQuestion(e.target.value)} />
          <br />
          <br />
          <button disabled={loading}>向知识库提问</button>
          {answer && (
            <>
              <h3>回答</h3>
              <div className="answer">{answer}</div>
              <h3>引用来源</h3>
              {sources.map((s, idx) => (
                <div className="item" key={idx}>
                  <strong>{s.title}</strong>
                  <p className="small">score: {s.score} · chunk #{s.chunk_index}</p>
                  <p>{s.preview}</p>
                </div>
              ))}
            </>
          )}
        </form>

        <div className="card">
          <h2>Reflection Agent</h2>
          <p className="small">根据你的文档和知识卡片生成阶段性复盘。</p>
          <button onClick={runReview} disabled={loading}>生成复盘</button>
          {review && (
            <div>
              <h3>总结</h3>
              <p>{review.summary}</p>
              <h3>高频主题</h3>
              {review.high_frequency_topics?.map((t: string) => <span className="badge" key={t}>{t}</span>)}
              <h3>下一步</h3>
              <ul>
                {review.next_actions?.map((x: string) => <li key={x}>{x}</li>)}
              </ul>
            </div>
          )}
        </div>
      </section>

      <section className="grid two">
        <div className="card">
          <h2>知识库文档</h2>
          {documents.map((doc) => (
            <div className="item" key={doc.id}>
              <strong>{doc.title}</strong>
              <p className="small">{doc.source_type} · {doc.created_at}</p>
              <p>{doc.summary}</p>
              {doc.keywords?.map((k) => <span className="badge" key={k}>{k}</span>)}
            </div>
          ))}
        </div>

        <div className="card">
          <h2>知识卡片</h2>
          {cards.map((card) => (
            <div className="item" key={card.id}>
              <strong>{card.concept}</strong>
              <p>{card.explanation}</p>
              <p className="small">{card.review_question}</p>
              {card.related?.map((k) => <span className="badge" key={k}>{k}</span>)}
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
