# AI-Interview 项目 RAG 实现原理

> 本文档详细说明 ai-interview 项目中 RAG（Retrieval-Augmented Generation，检索增强生成）知识库的实现原理、技术架构和核心流程。

---

## 一、什么是 RAG

**RAG = 检索（Retrieval）+ 增强（Augmented）+ 生成（Generation）**

传统的大模型问答只依赖模型训练时的知识，无法使用外部专有数据，且容易"幻觉"（自信地编造事实）。RAG 解决这个问题：

```
用户输入
   ↓
[检索器] 从知识库找到最相关的内容片段
   ↓
[Prompt 构建] 把检索结果拼接到大模型的 Prompt 里
   ↓
[大模型生成] 基于检索到的真实内容生成回答
```

本项目中 RAG 有两个用途：
1. **出题增强**：从题库里检索与候选人简历最相关的面试题，替代纯 AI 生成
2. **评分增强**：评分时携带题库中的标准答案作为评判依据，减少 AI 评分幻觉

---

## 二、整体技术架构

```
┌──────────────────────────────────────────────────────────────────────┐
│                         管理端前端 (Vue 3)                             │
│  题库管理页面 / 文档管理页面 / 检索测试页面                              │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ HTTP
┌──────────────────────────────▼───────────────────────────────────────┐
│                        FastAPI 后端                                    │
│                                                                       │
│   ┌───────────────┐   ┌──────────────────┐   ┌────────────────────┐ │
│   │ QuestionBank  │   │ KnowledgeService │   │    AIService       │ │
│   │ Service       │   │ (文档摄入+检索)   │   │ (LLM 调用层)       │ │
│   │ (题库CRUD+    │   │                  │   │                    │ │
│   │  向量化+检索)  │   └────────┬─────────┘   └──────────┬────────┘ │
│   └──────┬────────┘            │                         │          │
│          │          ┌──────────▼─────────────────────────▼────────┐ │
│          │          │          RAG 基础能力层                      │ │
│          │          │  文档加载 / 解析（PDF / MD / TXT）           │ │
│          │          │  RecursiveCharacterTextSplitter（分块）      │ │
│          │          │  DashScopeEmbeddings（阿里云，向量化）       │ │
│          │          └──────────┬─────────────────────────┬────────┘ │
└──────────┼───────────────────┼─────────────────────────┼───────────┘
           │                   │                         │
  ┌────────▼───────────────────▼──────┐      ┌──────────▼──────────┐
  │      PostgreSQL 16 + pgvector     │      │   阿里云 DashScope   │
  │                                   │      │  text-embedding-v3  │
  │  ┌──────────────────────────┐     │      │  (1024 维向量)       │
  │  │ question_bank            │     │      └─────────────────────┘
  │  │ - id, question, answer   │     │
  │  │ - embedding vector(1024) │     │
  │  └──────────────────────────┘     │
  │  ┌──────────────────────────┐     │
  │  │ knowledge_chunks         │     │
  │  │ - content (文档片段)     │     │
  │  │ - embedding vector(1024) │     │
  │  └──────────────────────────┘     │
  └───────────────────────────────────┘
```

### 技术选型总结

| 组件 | 选型 | 理由 |
|------|------|------|
| Embedding 模型 | 阿里云 DashScope `text-embedding-v3` | 中文效果好、¥0.0007/千 token、国内可用 |
| 向量数据库 | PostgreSQL + pgvector 扩展 | 复用现有 PG，零额外部署，HNSW 索引够用 |
| 编排框架 | LangChain 0.3.x | 标准化文档加载 / 切分接口 |
| 向量索引 | HNSW（Hierarchical Navigable Small World）| 比 IVFFlat 在中小规模下更快、无需预训练 |
| 相似度度量 | Cosine（余弦相似度）| 对文本语义匹配最常用 |

---

## 三、核心概念：向量化（Embedding）

### 3.1 什么是向量化

把一段文字转换为一个高维数值向量（如 1024 维的浮点数数组）。语义相近的文字，在向量空间中距离更近。

```
"Python 协程原理"    → [0.12, -0.34, 0.87, ...]  (1024 个数字)
"asyncio 事件循环"   → [0.11, -0.33, 0.85, ...]  (语义近 → 数字近)
"HTTP 状态码含义"    → [-0.56, 0.12, -0.23, ...] (语义远 → 数字远)
```

### 3.2 本项目使用 DashScope text-embedding-v3

```python
# app/services/common/embedding.py
from langchain_community.embeddings import DashScopeEmbeddings

embeddings = DashScopeEmbeddings(
    model="text-embedding-v3",      # 输出 1024 维向量
    dashscope_api_key=settings.DASHSCOPE_API_KEY,
)

# 单文本向量化
vector = await embeddings.aembed_query("Python GIL 机制")
# → [0.12, -0.34, 0.87, ...]  长度为 1024 的列表

# 批量向量化（每批最多 25 条，自动分批）
vectors = await embeddings.aembed_documents(["题目1", "题目2", ...])
```

### 3.3 题库题目的向量化策略

题目的 embedding 不只用题面，而是**题面 + 参考答案一起拼接**，让向量既代表"这道题问什么"，也代表"正确答案涉及哪些概念"，检索效果更准确：

```python
# app/services/backoffice/question_bank_service.py
def _build_embedding_text(question, reference_answer):
    parts = [question.strip()]
    if reference_answer:
        parts.append(f"参考答案：{reference_answer.strip()}")
    return "\n\n".join(parts)

# 示例：
# "请解释 Python GIL 机制\n\n参考答案：GIL 是 CPython 的全局解释器锁..."
```

---

## 四、向量存储：pgvector

### 4.1 pgvector 是什么

pgvector 是 PostgreSQL 的一个**扩展（Extension）**，给 PG 添加：
- `vector(n)` 数据类型（存储 n 维浮点数组）
- 相似度操作符（`<=>` 余弦距离、`<->` L2 距离）
- 向量索引（HNSW、IVFFlat）

```sql
-- 安装扩展（一次即可）
CREATE EXTENSION IF NOT EXISTS vector;

-- 在普通表里加一个向量列
ALTER TABLE question_bank ADD COLUMN embedding vector(1024);

-- 建 HNSW 索引（让 K 近邻检索飞速）
CREATE INDEX ix_question_bank_embedding
ON question_bank USING hnsw (embedding vector_cosine_ops);
```

### 4.2 两张向量表的设计

**`question_bank`**（题库题目）
```
id | category | position_tag | difficulty | question | reference_answer | embedding vector(1024)
```
- 每道题有一个 1024 维 embedding
- 检索时：把候选人简历技能 → 向量化 → 找最相似的题

**`knowledge_chunks`**（文档切片）
```
id | document_id | chunk_index | content | embedding vector(1024)
```
- 文档按 500 字一块切分，每块都有 embedding
- 检索时：把问题 → 向量化 → 找最相似的文档片段

---

## 五、文档摄入流水线

当管理员上传一份 PDF 文档（即知识库文档），系统经历以下流程：

```
管理员上传 PDF 文件
        │
        ▼
[API 层] 保存文件到磁盘，在 knowledge_documents 表
        插入记录（status=pending），立即返回 doc_id
        │
        ▼  (BackgroundTasks 异步执行)
[KnowledgeService.ingest_from_path -> ingest_document]
        │
        ├─→ pdfplumber.open() 提取所有页面文字
        │
        ├─→ RecursiveCharacterTextSplitter 切分
        │   chunk_size=500, chunk_overlap=50
        │   分隔符优先级: "\n\n" > "\n" > "。" > " "
        │
        ├─→ DashScope API 批量 Embedding（每批 25 条）
        │
        ├─→ 批量写入 knowledge_chunks 表（含 vector 列）
        │
        └─→ 更新 knowledge_documents.status = "indexed"
```

### 文本切分策略详解

`RecursiveCharacterTextSplitter` 是 LangChain 的递归分割器，优先在语义边界处切：

```python
splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,      # 每块最多 500 字
    chunk_overlap=50,    # 相邻块重叠 50 字（保留上下文）
    separators=["\n\n", "\n", "。", "！", "？", ".", " "],
)
```

切分示意：
```
原文 1000 字 → 块1(0-500字) + 块2(450-950字) + 块3(900-1000字)
                     重叠50字↗         重叠50字↗
```

重叠区域的作用：防止一个知识点恰好被切断在两块边界，导致哪块单独看都不完整。

---

## 六、题库 RAG 出题流程（核心）

这是本项目 RAG 最核心的业务流程——用向量检索题库替代 AI 随机出题。

### 6.1 三分支决策树

```
用户创建面试
      │
      ▼
构造检索 query
= "{target_position} {top_skills}"
例："python_backend 协程 异步 Redis 高并发"
      │
      ▼
向题库做向量检索
召回最多 N*2 道相似度 >= 0.7 的候选题
（第一次按岗位严格筛，不够再放宽）
      │
      ├── 召回数 >= N（题库充分）
      │         │
      │         ▼
      │   AIService.select_and_adapt_questions()
      │         │
      │         │  AI 工作：从候选题中挑 N 道
      │         │  · 优先与简历项目高度相关的
      │         │  · 难度由简到难排序
      │         │  · 可微调措辞贴近候选人背景
      │         │  · 返回保留 bank_id（标记来源）
      │         ▼
      │   返回 N 题，source="from_bank"
      │
      ├── 0 < 召回数 < N（题库不足）
      │         │
      │         ▼
      │   AIService.generate_with_seeds()
      │         │
      │         │  AI 工作：
      │         │  · 保留所有 k 道题库题（source="from_bank"）
      │         │  · 额外生成 N-k 道补齐（source="ai_fallback"）
      │         │  · 风格与题库题保持一致
      │         ▼
      │   返回 N 题（混合来源）
      │
      └── 召回数 = 0（题库为空）
                │
                ▼
          AIService.generate_questions()（原有逻辑）
          纯 AI 生成，source="ai_fallback"
```

### 6.2 为什么要两次召回

```python
# 第一次：严格按岗位筛选
candidates = await retrieve_questions(
    query=query,
    position_tag=target_position,  # 精准匹配
    min_score=0.7,
)

# 如果不够，第二次：放宽岗位限制（只用向量相似度）
if len(candidates) < total_questions:
    relaxed = await retrieve_questions(
        query=query,
        position_tag=None,  # 不限岗位
        min_score=0.7,
    )
    # 合并去重
```

目的：用严格筛选保证质量，用宽松筛选提高覆盖率，两者取并集。

### 6.3 相似度阈值的作用

```
相似度 0.7 = cosine_distance 0.3

相似度 = 1 - cosine_distance

配置项：QUESTION_BANK_MIN_SCORE=0.7
含义：只有相似度 >= 70% 的题才进入候选池
```

如果阈值设太高（如 0.9），题库召回率低，经常走 AI 兜底。
如果阈值设太低（如 0.3），召回太多不相关的题，AI 选题质量差。
**0.7 是经验值，可根据实际效果调整。**

---

## 七、评分增强：reference_answer 注入

题库题目带有管理员填写的 `reference_answer`（参考答案）和 `key_points`（采分要点）。这些信息在评分时注入 Prompt，让 AI 对照标准答案打分，而不是靠"直觉"：

```python
# app/services/client/ai_service.py
async def evaluate_answer(
    question, answer, resume_context, chat_history,
    reference_answer=None,  # 题库中的参考答案
    key_points=None,         # 题库中的关键采分点
):
    ref_block = ""
    if reference_answer:
        ref_block += f"\n【参考答案要点（评分依据，不要读给候选人）】：\n{reference_answer}\n"
    if key_points:
        ref_block += f"\n【关键采分点】：{json.dumps(key_points)}\n"

    # 注入到 Prompt
    system_prompt = "你是技术面试官...\n" + (
        "评分时请对照【参考答案要点】，候选人答中要点越多分越高。\n"
        if ref_block else ""
    )
    user_prompt = f"候选人答案：{answer}\n{ref_block}..."
```

**效果对比：**

| | 无 reference_answer | 有 reference_answer |
|--|--|--|
| 评分依据 | AI 凭训练知识 | 对照题库标准答案 |
| 幻觉风险 | 高（AI 可能评错）| 低（有明确标准） |
| 评语质量 | 泛泛而谈 | 具体指出缺失要点 |

---

## 八、文档 RAG 检索（用于答案评分增强 / 用户答疑）

文档 RAG 与题库 RAG 共用同一套 Embedding 基础设施，但检索目标不同：

- **题库 RAG**：目标是找最相关的**面试题**（结构化数据，有 category/difficulty 等字段）
- **文档 RAG**：目标是找最相关的**知识片段**（非结构化文本，从 PDF/MD 切分而来）

```python
# app/services/backoffice/knowledge_service.py
async def retrieve_chunks(query, db, k=4, category=None, min_score=0.3):
    query_vec = await embed_text(query)
    distance_threshold = 1.0 - min_score  # similarity=0.3 → distance=0.7

    stmt = (
        select(
            KnowledgeChunk.id,
            KnowledgeChunk.document_id,
            KnowledgeChunk.content,
            KnowledgeChunk.embedding.cosine_distance(query_vec).label("distance"),
        )
        .join(KnowledgeDocument, ...)
        .where(
            KnowledgeChunk.embedding.is_not(None),
            KnowledgeDocument.is_active == True,
            KnowledgeChunk.embedding.cosine_distance(query_vec) <= distance_threshold,
        )
        .order_by(KnowledgeChunk.embedding.cosine_distance(query_vec))
        .limit(k)
    )
```

---

## 九、数据流完整图

### 出题时的 RAG 数据流

```
[用户端]                    [后端]                    [DashScope]
 请求创建面试                  │                          │
  ─────────────────────────→  │                          │
                         构造 query                       │
                         "python_backend 协程 异步"       │
                               │ embed_text(query)        │
                               ─────────────────────────→│
                               ←─────────────────────────│
                              query_vector (1024维)        │
                               │                          │
                         pgvector cosine 检索             │
                         question_bank 表                 │
                         → Top K 候选题目                 │
                               │                          │
                         调 DeepSeek API                  │
                         select_and_adapt                 │
                         → 最终 N 道题                    │
                               │                          │
  ←─────────────────────────── │                          │
 返回第一道题                   │                          │
 (面试开始)                     │                          │
```

### 评分时的 RAG 数据流

```
[用户端]                    [后端]                    [DeepSeek]
 提交回答                      │                          │
  ─────────────────────────→  │                          │
                         取当前题的 reference_answer      │
                         （来自 questions_data 里存的）   │
                               │                          │
                         构建 Prompt                      │
                         ┌─────────────────────┐         │
                         │ 系统提示词           │         │
                         │ 评分标准             │         │
                         │ 【参考答案要点】      │  ←←←← 题库题的 reference_answer
                         │ 【关键采分点】       │  ←←←← 题库题的 key_points
                         │ ────────────        │         │
                         │ 候选人背景           │         │
                         │ 对话历史             │         │
                         │ 候选人回答           │         │
                         └─────────────────────┘         │
                               │ 调 DeepSeek API          │
                               ─────────────────────────→│
                               ←─────────────────────────│
                              评分 + 反馈 (SSE 流式)       │
  ←─────────────────────────── │                          │
 实时看到评语                    │                          │
```

---

## 十、HNSW 向量索引原理

pgvector 支持 HNSW（Hierarchical Navigable Small World）索引，是目前向量数据库中最流行的近似最近邻（ANN）算法。

### 核心思想

把向量按层次结构组织成图：
- 顶层：稀疏的长程连接（快速跳转到大致区域）
- 底层：密集的短程连接（精细搜索）

查询时：从顶层入口进入 → 逐层下降 → 在底层找最近邻。

```
Layer 2: ●────────────────●
         (稀疏，大跳转)

Layer 1: ●───●       ●───●
         (中等连接)

Layer 0: ●─●─●─●─●─●─●─●
         (密集，精细)
           ↑查询向量落点
```

### 为什么比全量扫描快

- 全量扫描：对 1000 道题，每次都计算 1000 次余弦距离
- HNSW：只计算约 `log(N)` 次，1000 题只需约 10 次

### 本项目的索引配置

```sql
CREATE INDEX ix_question_bank_embedding
ON question_bank USING hnsw (embedding vector_cosine_ops);
-- vector_cosine_ops = 用余弦距离度量相似度
```

**注意**：HNSW 是**近似**算法，可能不返回绝对精确的 Top K，但精度与速度的权衡已经足够实际应用。

---

## 十一、相似度计算公式

### 余弦相似度（Cosine Similarity）

$$\text{cosine\_similarity}(A, B) = \frac{A \cdot B}{|A| \cdot |B|}$$

- 值域：-1 到 1（文本场景下一般 0 到 1）
- 1 = 完全相同方向（语义完全相似）
- 0 = 垂直（语义无关）

### pgvector 的 cosine_distance

pgvector 的 `<=>` 操作符返回**余弦距离**（不是相似度）：

```
cosine_distance = 1 - cosine_similarity
```

因此代码里的换算：
```python
min_score = 0.7  # 要求相似度 >= 0.7
distance_threshold = 1 - min_score  # 即 distance <= 0.3

# 检索条件
.where(embedding.cosine_distance(query_vec) <= distance_threshold)

# 返回相似度时再换回来
similarity = 1 - float(row["distance"])
```

---

## 十二、配置参数说明

| 参数 | 默认值 | 含义 |
|------|--------|------|
| `DASHSCOPE_API_KEY` | 必填 | 阿里云 DashScope API Key |
| `KNOWLEDGE_EMBEDDING_MODEL` | `text-embedding-v3` | 向量化模型名称 |
| `KNOWLEDGE_EMBEDDING_DIM` | `1024` | 向量维度（换模型必须重建所有索引）|
| `KNOWLEDGE_CHUNK_SIZE` | `500` | 文档切片最大字符数 |
| `KNOWLEDGE_CHUNK_OVERLAP` | `50` | 相邻切片重叠字符数 |
| `KNOWLEDGE_TOP_K` | `4` | 文档检索默认返回数量 |
| `KNOWLEDGE_MIN_SCORE` | `0.3` | 文档检索最低相似度阈值 |
| `QUESTION_BANK_MIN_SCORE` | `0.7` | 题库检索最低相似度阈值（更严格）|
| `QUESTION_BANK_RECALL_FACTOR` | `2` | 题库召回倍数（N*2 个候选再筛 N 个）|
| `QUESTION_BANK_TOP_K` | `20` | 题库检索最大返回数量 |

---

## 十三、新增的数据库表

### `question_bank`（题库 + 向量）

```sql
CREATE TABLE question_bank (
    id              SERIAL PRIMARY KEY,
    category        VARCHAR(50) NOT NULL,    -- technical/behavioral/...
    position_tag    VARCHAR(100) NOT NULL,   -- python_backend/vue_frontend/...
    difficulty      VARCHAR(20) NOT NULL,    -- easy/medium/hard
    question        TEXT NOT NULL,           -- 题面
    reference_answer TEXT,                   -- 参考答案（用于评分）
    key_points      JSONB,                   -- 关键采分点数组
    tags            JSONB,                   -- 标签数组
    embedding       vector(1024),            -- 向量（题面+答案拼接后）
    embedding_text  TEXT,                    -- 用于生成 embedding 的原文（调试）
    source          VARCHAR(50) DEFAULT 'manual',
    use_count       INTEGER DEFAULT 0,       -- 被选为面试题的次数
    is_active       BOOLEAN DEFAULT TRUE,
    created_by      INTEGER REFERENCES admins(id),
    created_at      TIMESTAMP WITH TIME ZONE,
    updated_at      TIMESTAMP WITH TIME ZONE
);

-- 向量检索索引
CREATE INDEX ON question_bank USING hnsw (embedding vector_cosine_ops);
-- 元数据筛选索引
CREATE INDEX ON question_bank (is_active, position_tag, difficulty);
```

### `knowledge_documents`（文档元数据）

```sql
CREATE TABLE knowledge_documents (
    id          SERIAL PRIMARY KEY,
    title       VARCHAR(200) NOT NULL,
    file_name   VARCHAR(255),
    file_url    VARCHAR(500),             -- 本地磁盘路径或 S3 URL
    file_type   VARCHAR(20),              -- pdf/md/txt
    file_size   BIGINT,
    category    VARCHAR(50),              -- python/java/vue/...
    tags        JSONB,
    description TEXT,
    chunk_count INTEGER DEFAULT 0,
    status      VARCHAR(20) DEFAULT 'pending',  -- pending/indexing/indexed/failed
    error_message TEXT,
    uploaded_by INTEGER REFERENCES admins(id),
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMP WITH TIME ZONE,
    updated_at  TIMESTAMP WITH TIME ZONE
);
```

### `knowledge_chunks`（文档切片 + 向量）

```sql
CREATE TABLE knowledge_chunks (
    id          SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES knowledge_documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,         -- 在文档中的顺序
    content     TEXT NOT NULL,            -- 切片文本
    content_hash VARCHAR(64),             -- SHA256（去重用）
    embedding   vector(1024),             -- 切片向量
    metadata    JSONB,                    -- 页码等元信息
    created_at  TIMESTAMP WITH TIME ZONE,
    updated_at  TIMESTAMP WITH TIME ZONE
);

-- 向量检索索引
CREATE INDEX ON knowledge_chunks USING hnsw (embedding vector_cosine_ops);
```

---

