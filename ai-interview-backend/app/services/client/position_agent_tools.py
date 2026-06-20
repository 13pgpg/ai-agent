"""
岗位匹配 Agent 的工具集（LangChain @tool）

5 个工具：
  1. get_parsed_resume       - 读取已解析的简历
  2. build_candidate_profile - 提炼候选人画像（调 DeepSeek）
  3. match_positions         - 从 position_templates 表匹配岗位
  4. get_position_interview_focus - 获取某岗位的面试方向
  5. start_mock_interview    - 启动一次专项模拟面试

设计要点：
- 每个工具内部自管 DB session（LangChain @tool 无法接 FastAPI Depends）
- 工具的 docstring 决定 LLM 是否会调用它，必须写得准确
- 输入输出尽量简单（dict / str / int），便于 LLM 调用
"""
import json
import logging
from typing import Optional
from langchain_core.tools import tool
from sqlalchemy import select
from app.db.base import get_session_local
from app.models.resume import Resume
from app.models.position_template import PositionTemplate
from app.services.client.ai_service import AIService
from app.services.backoffice.position_template_service import PositionTemplateService

logger = logging.getLogger(__name__)


# ── 工具 1：读取已解析的简历 ────────────────────────────────────────────

@tool
async def get_parsed_resume(resume_id: int) -> dict:
    """
    根据简历 ID 获取候选人的结构化简历信息（包含技能、教育背景、项目经历等）。
    在做岗位匹配之前必须先调用本工具获取候选人简历内容。

    Args:
        resume_id: 简历的数据库主键 ID

    Returns:
        包含 user_id, target_position, parsed_resume 的字典；
        parsed_resume 内含 name, education, skills, experience, projects, summary
    """
    async with get_session_local()() as db:
        resume = await db.get(Resume, resume_id)
        if not resume:
            return {"error": f"简历 {resume_id} 不存在"}
        if resume.status != "completed":
            return {"error": f"简历 {resume_id} 尚未解析完成（当前状态: {resume.status}）"}

        try:
            parsed = json.loads(resume.parsed_content) if resume.parsed_content else {}
        except json.JSONDecodeError:
            parsed = {}

        return {
            "resume_id": resume.id,
            "user_id": resume.user_id,
            "target_position": resume.target_position,
            "parsed_resume": parsed,
        }


# ── 工具 2：构建候选人画像 ──────────────────────────────────────────────

@tool
async def build_candidate_profile(parsed_resume: dict) -> dict:
    """
    基于结构化简历提炼候选人画像，输出技术栈分级、项目方向、强项、短板和经验层级。
    在拿到 get_parsed_resume 的结果后调用本工具，为后续岗位匹配做准备。

    Args:
        parsed_resume: 来自 get_parsed_resume 的 parsed_resume 字段

    Returns:
        包含 experience_level, primary_stack, secondary_stack, project_directions,
        strong_points, weak_points, position_hints 的字典
    """
    if not parsed_resume:
        return {"error": "parsed_resume 为空"}

    messages = [
        {
            "role": "system",
            "content": (
                "你是一个资深技术面试官 + HR 顾问。"
                "请根据候选人结构化简历，提炼成画像信息。\n"
                "必须返回纯 JSON 格式（不要 markdown 代码块），包含字段：\n"
                '{\n'
                '  "experience_level": "campus / junior / mid / senior",\n'
                '  "primary_stack": ["核心技术栈，最多 8 个"],\n'
                '  "secondary_stack": ["次要技术栈"],\n'
                '  "project_directions": ["项目方向标签，如 电商后端 / AI应用 / 数据分析"],\n'
                '  "strong_points": ["3 条具体优势"],\n'
                '  "weak_points": ["3 条具体不足"],\n'
                '  "position_hints": ["建议匹配的岗位标签，如 python_backend / vue_frontend"]\n'
                '}\n'
                "评估标准：\n"
                "- 在校学生 / 应届生只有实习经历 → campus\n"
                "- 1-3 年经验 → junior\n"
                "- 3-5 年经验 → mid\n"
                "- 5 年以上 → senior\n"
                "position_hints 候选值（必须在内）：python_backend / java_backend / vue_frontend "
                "/ react_frontend / ai_application / fullstack / mobile_android / devops"
            ),
        },
        {
            "role": "user",
            "content": f"候选人简历：\n{json.dumps(parsed_resume, ensure_ascii=False)}",
        },
    ]
    raw = await AIService._chat(messages, temperature=0.3)
    try:
        return AIService._extract_json(raw)
    except Exception as e:
        logger.error(f"build_candidate_profile JSON 解析失败: {e}, raw: {raw[:200]}")
        return {"error": "AI 输出解析失败", "raw": raw[:200]}


# ── 工具 3：岗位匹配 ────────────────────────────────────────────────────

def _calculate_match_score(profile: dict, template: PositionTemplate) -> tuple[float, list, list]:
    """
    计算候选人画像与岗位模板的匹配度。
    返回 (score, matched_skills, missing_skills)
    """
    candidate_skills = set()
    for stack in (profile.get("primary_stack") or []) + (profile.get("secondary_stack") or []):
        candidate_skills.add(str(stack).lower().strip())

    core = [s.lower().strip() for s in (template.core_skills or [])]
    nice = [s.lower().strip() for s in (template.nice_to_have_skills or [])]

    # 核心技能匹配
    core_matched = [s for s in core if any(s in cs or cs in s for cs in candidate_skills)]
    nice_matched = [s for s in nice if any(s in cs or cs in s for cs in candidate_skills)]
    core_score = len(core_matched) / max(len(core), 1)
    nice_score = len(nice_matched) / max(len(nice), 1) if nice else 0

    # 项目方向匹配（加分项）
    project_score = 0
    candidate_dirs = [str(d).lower() for d in (profile.get("project_directions") or [])]
    template_keywords = [str(k).lower() for k in (template.project_keywords or [])]
    if candidate_dirs and template_keywords:
        overlap = sum(1 for d in candidate_dirs if any(kw in d or d in kw for kw in template_keywords))
        project_score = overlap / max(len(template_keywords), 1)

    # position_hints 强匹配（候选人画像主动指向）
    hints_bonus = 0.15 if template.position_tag in (profile.get("position_hints") or []) else 0

    # 综合分（控制在 0-1）
    score = min(1.0, core_score * 0.6 + nice_score * 0.15 + project_score * 0.1 + hints_bonus)

    # 缺失技能
    missing = [s for s in (template.core_skills or []) if s.lower().strip() not in [m.lower() for m in core_matched]]
    matched = [s for s in (template.core_skills or []) if s.lower().strip() in [m.lower() for m in core_matched]]

    return round(score, 4), matched, missing


@tool
async def match_positions(candidate_profile: dict, top_n: int = 3) -> dict:
    """
    基于候选人画像，从岗位模板库匹配最适合的 1-3 个岗位。
    必须在调用 build_candidate_profile 之后才能使用本工具。

    Args:
        candidate_profile: 来自 build_candidate_profile 的输出
        top_n: 返回 Top N 个推荐岗位（默认 3）

    Returns:
        recommended_positions 字段为列表，每条含 position_tag, title, match_score,
        reasons, missing_skills, matched_skills
    """
    if not candidate_profile or candidate_profile.get("error"):
        return {"error": "candidate_profile 无效"}

    async with get_session_local()() as db:
        templates = await PositionTemplateService.get_active_list(db)

    if not templates:
        return {"recommended_positions": [], "warning": "岗位模板库为空"}

    scored = []
    for t in templates:
        score, matched, missing = _calculate_match_score(candidate_profile, t)
        scored.append((t, score, matched, missing))

    scored.sort(key=lambda x: x[1], reverse=True)
    top = scored[:top_n]

    recommended = []
    for t, score, matched, missing in top:
        reasons = []
        if matched:
            reasons.append(f"具备 {', '.join(matched[:3])} 等核心技能")
        if t.position_tag in (candidate_profile.get("position_hints") or []):
            reasons.append("候选人画像与该岗位方向一致")
        directions = candidate_profile.get("project_directions") or []
        keywords = t.project_keywords or []
        if directions and keywords:
            overlap = [d for d in directions if any(str(kw).lower() in str(d).lower() for kw in keywords)]
            if overlap:
                reasons.append(f"项目方向匹配（{overlap[0]}）")
        if not reasons:
            reasons.append("整体技术栈与岗位要求有一定重合")

        recommended.append({
            "position_tag": t.position_tag,
            "title": t.title,
            "category": t.category,
            "level": t.level,
            "match_score": score,
            "matched_skills": matched,
            "missing_skills": missing[:5],
            "reasons": reasons,
        })

    return {"recommended_positions": recommended}


# ── 工具 4：获取岗位面试方向 ────────────────────────────────────────────

@tool
async def get_position_interview_focus(position_tag: str) -> dict:
    """
    根据岗位标签返回该岗位的推荐面试方向、推荐难度、推荐题数和题库 RAG 检索关键词。
    在确定推荐岗位后调用本工具，可拿到启动模拟面试所需的参数。

    Args:
        position_tag: 岗位内部标识，如 python_backend / java_backend

    Returns:
        包含 focus_topics, recommended_difficulty, recommended_question_count,
        recommended_query_keywords 的字典
    """
    async with get_session_local()() as db:
        template = await PositionTemplateService.get_by_tag(db, position_tag)

    if not template:
        return {"error": f"岗位标签 {position_tag} 不存在或已禁用"}
    if not template.is_active:
        return {"error": f"岗位 {position_tag} 已禁用"}

    return {
        "position_tag": template.position_tag,
        "title": template.title,
        "focus_topics": template.focus_topics or [],
        "recommended_difficulty": template.recommended_difficulty,
        "recommended_question_count": template.recommended_question_count,
        "recommended_query_keywords": template.recommended_query_keywords or [],
        "jd_summary": template.jd_summary,
    }


# ── 工具 5：启动专项模拟面试 ────────────────────────────────────────────

@tool
async def start_mock_interview(
    resume_id: int,
    position_tag: str,
    difficulty: Optional[str] = None,
    total_questions: Optional[int] = None,
) -> dict:
    """
    根据指定的简历和岗位标签启动一次专项模拟面试。
    本工具会自动复用已有的题库 RAG 出题流程。
    通常在用户从推荐岗位列表中选定一个岗位后调用。

    Args:
        resume_id: 简历 ID
        position_tag: 目标岗位标签
        difficulty: 难度，可选 easy / medium / hard，不传则使用岗位默认
        total_questions: 题数，不传则使用岗位默认

    Returns:
        包含 interview_id, position_tag, first_question, total_questions 的字典
    """
    from app.services.client.interview_service import InterviewService

    async with get_session_local()() as db:
        # 1. 取岗位模板拿默认参数
        template = await PositionTemplateService.get_by_tag(db, position_tag)
        if not template or not template.is_active:
            return {"error": f"岗位 {position_tag} 不存在或已禁用"}

        # 2. 取简历
        resume = await db.get(Resume, resume_id)
        if not resume:
            return {"error": f"简历 {resume_id} 不存在"}

        final_difficulty = difficulty or template.recommended_difficulty
        final_total = total_questions or template.recommended_question_count

        try:
            result = await InterviewService.start_interview(
                db=db,
                user_id=resume.user_id,
                resume_id=resume_id,
                target_position=template.title,
                difficulty=final_difficulty,
                total_questions=final_total,
            )
            result["position_tag"] = position_tag
            return result
        except Exception as e:
            logger.error(f"启动模拟面试失败: {e}")
            return {"error": f"启动面试失败: {str(e)}"}


# ── 工具列表（供 AgentExecutor 注入）─────────────────────────────────────

POSITION_AGENT_TOOLS = [
    get_parsed_resume,
    build_candidate_profile,
    match_positions,
    get_position_interview_focus,
    start_mock_interview,
]
