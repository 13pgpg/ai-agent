# AI Interview

一个面向求职场景的 **AI 模拟面试系统**。  
项目围绕“**简历解析 -> 岗位匹配 -> RAG 出题 -> AI 评分 -> 面试报告**”构建了完整闭环，重点体现了我在 **AI 应用开发、工程化落地、RAG 设计、Agent 工作流编排** 方面的能力。

---

## 项目简介

传统模拟面试系统通常只解决“出题”和“评分”，而这个项目进一步把 AI 放到了求职链路前面：

- 用户上传简历后，系统先调用 AI 解析简历并落库
- 基于岗位匹配 Agent，对候选人画像进行分析并推荐更适合的岗位方向
- 进入目标岗位的专项模拟面试
- 基于题库 RAG 召回高相关题目，并结合参考答案与采分点进行 AI 评分
- 输出结构化面试报告，帮助用户明确能力差距和下一步学习方向

这个项目不是单一 Prompt Demo，而是一个包含 **前端、后端、数据库、异步任务、向量检索、Agent 编排、Docker 部署** 的完整 AI 应用项目。

---

## 核心亮点

### 1. 面向真实业务的 AI 闭环

此项目实现了完整的求职场景闭环：

- 简历上传与解析
- 岗位匹配 Agent
- 题库 RAG 面试
- AI 评分与反馈
- 面试报告输出



### 2. 题库 RAG

项目中实现了两套 RAG，其中真正接入主业务的是 **题库 RAG**：

- 管理员维护结构化题库：题目、参考答案、采分点
- 将题目与参考答案拼接后做向量化
- 使用 `PostgreSQL + pgvector` 存储 embedding
- 面试发起时，结合岗位和简历技能做语义召回
- 当题库不足时，采用“二次召回 + AI 兜底补全”的策略保证流程稳定

相比纯 AI 生成题目，这种方式让题目更贴近岗位，也让评分更可控。

### 3. 评分不是“凭感觉”，而是基于题库标准答案

用户回答问题后，系统不会直接让大模型自由打分，而是把题库中的：

- `reference_answer`
- `key_points`

一起注入评分 Prompt，作为评分参考依据。  
这样可以显著提升评分稳定性，减少大模型“凭感觉评分”的不确定性。

### 4. 实现了岗位匹配 Agent，而不是单纯表单跳转

项目含有 **岗位匹配 Agent**功能，用于把“简历解析”和“模拟面试”连接起来。

它不是凭空推荐岗位，而是：

- 先读取已解析的结构化简历
- 构建候选人画像
- 再与系统中的岗位模板库做匹配
- 输出推荐岗位、推荐理由、能力差距和下一步建议

技术上使用了 **LangChain Tool Calling Agent**，并配合工具调用工作流来保证结果可解释、可调试。

### 5. 项目具备工程化

项目中体现了较完整的工程化思维：

- 前后端分离架构
- Docker Compose 本地一键启动
- PostgreSQL / Redis / Celery 异步任务协同
- 静态文件挂载与容器内服务通信
- API 分层、Service 分层、Schema 分层
- 向量检索、异步任务、SSE 流式输出


---

## 技术栈

### 后端

- FastAPI
- SQLAlchemy 2.x
- PostgreSQL
- pgvector
- Redis
- Celery
- Alembic
- Uvicorn

### AI / RAG / Agent

- DeepSeek API
- OpenAI Compatible SDK
- LangChain
- LangChain OpenAI
- DashScope Embedding
- RecursiveCharacterTextSplitter

### 前端

- Vue 3
- Vite
- Vue Router
- Pinia
- Axios

### 工程与部署

- Docker / Docker Compose
- Nginx
- Linux

---

## 系统架构

```text
[用户前端]
   ├─ 上传简历
   ├─ 岗位匹配
   ├─ 模拟面试
   └─ 查看报告
        │
        ▼
[FastAPI 后端]
   ├─ 简历解析服务
   ├─ 岗位匹配 Agent
   ├─ 面试服务
   ├─ 题库管理
   └─ 知识库管理
        │
        ├─ DeepSeek：简历解析 / 出题 / 评分 / 报告
        ├─ DashScope：Embedding
        ├─ PostgreSQL + pgvector：结构化数据 + 向量检索
        ├─ Redis：缓存 / Broker
        └─ Celery：异步任务
```

---

## 业务流程

### 1. 简历解析

用户上传 PDF 简历后，系统会：

1. 提取 PDF 文本
2. 调用 DeepSeek 解析成结构化简历
3. 生成简历分析结果
4. 将 `parsed_content` 与 `analysis` 写入数据库

### 2. 岗位匹配 Agent

Agent 主流程：

1. 读取已解析简历
2. 构建候选人画像
3. 匹配岗位模板
4. 获取岗位面试重点
5. 输出推荐岗位、推荐理由、能力差距和学习建议

### 3. 题库 RAG 出题

发起面试时，系统会：

1. 根据目标岗位 + 简历技能构造检索 query
2. 调用 DashScope Embedding 生成 query vector
3. 在 `question_bank` 中用 `pgvector cosine_distance` 召回候选题
4. 如果候选题足够，由 AI 选题并微调
5. 如果候选题不足，触发二次召回或 AI 兜底补全

### 4. AI 评分

用户提交回答后，系统会：

1. 获取当前题对应的 `reference_answer` 和 `key_points`
2. 构造评分 Prompt
3. 调用 DeepSeek 评分并流式返回反馈
4. 保存单题得分、反馈、整场报告

---

## 项目结构

```text
ai-interview/
├─ ai-interview-backend/     # FastAPI + PostgreSQL + Redis + Celery
├─ ai-interview-frontend/    # 用户端前端
├─ ai-interview-admin/       # 管理端前端
├─ 面试要点.md               # 项目口述与面试整理
├─ 项目RAG实现原理.md         # RAG 技术链路说明
```

---



## 工程化设计亮点

### 分层清晰

后端采用较清晰的分层：

- `api`：接口层
- `schemas`：请求/响应模型
- `services`：业务逻辑层
- `models`：数据库模型

这样做的好处是：

- 业务逻辑更集中
- 便于单独维护 RAG、Agent、简历、面试等模块
- 后续扩展更自然

### AI 能力统一封装

`ai_service.py` 不是简单的模型调用文件，而是项目里的 **AI 能力中枢**，统一封装了：

- 简历解析
- 简历分析
- 面试出题
- 回答评分
- 流式反馈
- 报告生成
- 题库补题与微调

### Agent 采用工具调用工作流

岗位匹配 Agent 不是“一个大 Prompt 全部搞定”，而是显式拆成多步工具调用：

- `get_parsed_resume`
- `build_candidate_profile`
- `match_positions`
- `get_position_interview_focus`
- `start_mock_interview`

这样结果更稳定，也便于调试和展示 Agent 的执行过程。

### 兼顾开发效率与可部署性

项目提供 Docker Compose 开发环境，能够快速拉起：

- App
- PostgreSQL
- Redis
- Celery Worker
- Celery Beat

对 AI 应用项目来说，这一点很重要，因为它体现的是“可运行、可联调、可部署”的完整能力。

---

## 启动方式

### 1. 启动后端

进入：

```bash
cd ai-interview-backend
```

使用 Docker Compose 启动：

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

### 2. 启动用户端前端

进入：

```bash
cd ai-interview-frontend
```

安装依赖并启动：

```bash
npm install
npm run dev
```

### 3. 启动管理端前端

进入：

```bash
cd ai-interview-admin
```

安装依赖并启动：

```bash
npm install
npm run dev
```

> 说明：实际运行前需要补充 `.env` 配置，例如数据库、Redis、DeepSeek、DashScope 等相关参数。



---