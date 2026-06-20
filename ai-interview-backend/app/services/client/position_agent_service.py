"""
岗位匹配 Agent 编排层

设计要点：
- 用 LangChain `create_tool_calling_agent` + `AgentExecutor` 把 5 个工具串起来
- LLM 用 ChatOpenAI 包装 DeepSeek（DeepSeek API 兼容 OpenAI Function Calling）
- 系统 Prompt 严格规定工作流和最终输出格式
- 最终输出 JSON 字符串，由 service 层解析后返给前端
"""
import json
import logging
from langchain_openai import ChatOpenAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate

from app.core.config import settings
from app.services.client.ai_service import AIService
from app.services.client.position_agent_tools import POSITION_AGENT_TOOLS

logger = logging.getLogger(__name__)


# ── LLM 配置 ────────────────────────────────────────────────────────────

_llm: ChatOpenAI | None = None

def get_llm() -> ChatOpenAI:
    """单例 ChatOpenAI 实例（包装 DeepSeek）"""
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            model=settings.DEEPSEEK_MODEL,
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
            temperature=0.3,
            timeout=120,
        )
    return _llm


# ── 系统 Prompt ─────────────────────────────────────────────────────────

SYSTEM_PROMPT = """你是一个专业的岗位匹配 AI 顾问，目标是帮助求职者找到最合适的正式岗位。

# 工作流程（严格按此顺序调用工具）

1. 调用 `get_parsed_resume` 获取候选人简历
2. 把上一步返回的 parsed_resume 传给 `build_candidate_profile`，提炼候选人画像
3. 把画像传给 `match_positions`，匹配 Top 3 推荐岗位
4. 对推荐 Top 1 的岗位调用 `get_position_interview_focus`，获取它的面试方向
5. 综合所有工具结果，输出最终的结构化推荐 JSON

# 重要规则

- 不要跳过任何步骤
- 不要在工具调用之外编造信息
- 推荐理由要具体可解释（结合候选人项目/技能），不要泛泛而谈
- 缺失能力要可执行，便于用户改进
- 最终输出**必须**是纯 JSON 格式（不要包 markdown 代码块），结构如下：

```json
{{
  "candidate_profile": {{
    "experience_level": "campus / junior / mid / senior",
    "primary_stack": [...],
    "secondary_stack": [...],
    "project_directions": [...],
    "strong_points": [...],
    "weak_points": [...]
  }},
  "recommended_positions": [
    {{
      "position_tag": "...",
      "title": "...",
      "match_score": 0.84,
      "reasons": [...],
      "missing_skills": [...]
    }}
  ],
  "top_position_focus": {{
    "position_tag": "...",
    "focus_topics": [...],
    "recommended_difficulty": "...",
    "recommended_question_count": 8
  }},
  "next_actions": [
    "3 条具体可执行的下一步建议",
    "结合缺失技能给出练习方向",
    "推荐进入哪个岗位的模拟面试"
  ]
}}
```

# 注意

- 输出严格按上述 JSON 结构，不要多加字段
- next_actions 要 3 条左右，结合最匹配岗位的 focus_topics 和缺失技能给出具体建议
- 如果某个工具返回 error，把错误信息透传到最终输出的 next_actions 里，不要继续调用后续工具
"""


_prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])


# ── 全局 Agent 实例（懒加载）────────────────────────────────────────────

_agent_executor: AgentExecutor | None = None

def get_agent_executor() -> AgentExecutor:
    """单例 AgentExecutor"""
    global _agent_executor
    if _agent_executor is None:
        agent = create_tool_calling_agent(
            llm=get_llm(),
            tools=POSITION_AGENT_TOOLS,
            prompt=_prompt,
        )
        _agent_executor = AgentExecutor(
            agent=agent,
            tools=POSITION_AGENT_TOOLS,
            verbose=True,                    # 终端能看到每一步推理过程，便于调试
            max_iterations=10,               # 最多 10 轮工具调用，防止死循环
            handle_parsing_errors=True,      # LLM 输出格式错误时自动重试
            return_intermediate_steps=True,  # 返回中间步骤，前端可视化用
        )
    return _agent_executor


# ── 对外服务 ────────────────────────────────────────────────────────────

class PositionAgentService:

    @staticmethod
    async def run_agent(
        resume_id: int,
        target_direction: str | None = None,
    ) -> dict:
        """
        运行岗位匹配 Agent，返回结构化推荐结果。

        Args:
            resume_id: 简历 ID
            target_direction: 用户期望方向（可选），如 "Python 后端"

        Returns:
            {
                "result": {...},          # Agent 最终输出 JSON
                "intermediate_steps": [...]  # 调用过的工具步骤摘要
            }
        """
        user_input = f"我的简历 ID 是 {resume_id}，请帮我做岗位匹配。"
        if target_direction:
            user_input += f"我想找的方向是：{target_direction}。"

        logger.info(f"[PositionAgent] 开始运行，resume_id={resume_id}")

        try:
            agent_executor = get_agent_executor()
            response = await agent_executor.ainvoke({"input": user_input})
        except Exception as e:
            logger.error(f"[PositionAgent] AgentExecutor 异常: {e}")
            return {
                "result": {"error": f"Agent 执行失败: {str(e)}"},
                "intermediate_steps": [],
            }

        raw_output = response.get("output", "")
        logger.info(f"[PositionAgent] 完成，raw_output 长度: {len(raw_output)}")

        # 解析最终 JSON
        try:
            result = AIService._extract_json(raw_output)
        except Exception as e:
            logger.error(f"[PositionAgent] 输出 JSON 解析失败: {e}, raw: {raw_output[:300]}")
            result = {
                "error": "Agent 最终输出格式异常",
                "raw_output": raw_output[:1000],
            }

        # 摘要中间步骤（不返回完整工具调用结果，避免响应过大）
        steps_summary = []
        for step in response.get("intermediate_steps", []):
            try:
                action, observation = step
                tool_name = getattr(action, "tool", "unknown")
                tool_input = getattr(action, "tool_input", {})
                steps_summary.append({
                    "tool": tool_name,
                    "input_preview": str(tool_input)[:200],
                    "output_preview": str(observation)[:200],
                })
            except Exception:
                continue

        return {
            "result": result,
            "intermediate_steps": steps_summary,
        }
