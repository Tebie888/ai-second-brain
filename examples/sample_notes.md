# Transformer 与 RAG

Transformer 使用 self-attention 建模 token 之间的关系，相比传统 RNN 更适合并行计算。

RAG（Retrieval-Augmented Generation）通过检索外部知识增强大模型回答能力，降低幻觉。

在 AI Agent 系统中：

- Transformer 负责语言理解与推理
- Embedding 用于向量检索
- RAG 负责知识增强
- Reflection Loop 用于自我复盘
- Memory System 用于长期记忆

AI Second Brain 的核心目标是构建长期知识管理能力，而不仅仅是问答。
