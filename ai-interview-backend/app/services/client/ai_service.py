import json
import logging
import re
from typing import Dict, List, Optional
from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

# DeepSeek 使用 OpenAI 兼容 API
client = AsyncOpenAI(
    api_key=settings.DEEPSEEK_API_KEY,
    base_url=settings.DEEPSEEK_BASE_URL
)


class AIService:
    """DeepSeek AI 服务 - 面试模拟核心"""

    @staticmethod
    async def _chat(messages: list, temperature: float = 0.7) -> str:
        """基础对话补全调用"""
        try:
            response = await client.chat.completions.create(
                model=settings.DEEPSEEK_MODEL,
                messages=messages,
                temperature=temperature,
                max_tokens=2000
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"DeepSeek API 调用失败: {e}")
            raise

    @staticmethod
    async def _chat_stream(messages: list, temperature: float = 0.7):
        """流式对话补全调用，逐块返回文本"""
        try:
            stream = await client.chat.completions.create(
                model=settings.DEEPSEEK_MODEL,
                messages=messages,
                temperature=temperature,
                max_tokens=2000,
                stream=True
            )
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"DeepSeek 流式 API 调用失败: {e}")
            raise

    @staticmethod
    def _extract_json(text: str):
        """从 AI 响应中提取 JSON，兼容 markdown 包裹、前后解释文字等情况"""
        if isinstance(text, (dict, list)):
            return text

        text = (text or "").strip()
        if not text:
            raise ValueError("AI 返回内容为空，无法提取 JSON")

        decoder = json.JSONDecoder()

        # 1. 最理想情况：整段就是 JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 2. 常见情况：```json ... ``` 代码块
        fenced_blocks = re.findall(r"```(?:json)?\s*([\s\S]*?)```", text, flags=re.IGNORECASE)
        for block in fenced_blocks:
            block = block.strip()
            if not block:
                continue
            try:
                return json.loads(block)
            except json.JSONDecodeError:
                pass

        # 3. 宽松情况：文本中夹带一段 JSON，尝试从第一个 { 或 [ 开始 raw_decode
        start_positions = [i for i in (text.find("{"), text.find("[")) if i != -1]
        for start in sorted(start_positions):
            snippet = text[start:].strip()
            try:
                obj, _ = decoder.raw_decode(snippet)
                return obj
            except json.JSONDecodeError:
                continue

        raise ValueError(f"无法从模型输出中提取 JSON: {text[:300]}")

    @staticmethod
    async def parse_resume(resume_text: str) -> dict:
        """解析简历文本，提取结构化信息（姓名、学历、技能、经历等）"""
        messages = [
            {
                "role": "system",
                "content": (
                    "你是一个专业的简历分析师。请解析简历内容，提取结构化信息。"
                    "必须返回纯JSON格式（不要markdown代码块），包含以下字段：\n"
                    '{"name": "姓名", "education": "学历信息", '
                    '"skills": ["技能列表"], "experience": ["工作/实习经历"], '
                    '"projects": ["项目经历"], "summary": "一句话总结候选人背景"}'
                )
            },
            {
                "role": "user",
                "content": f"请解析以下简历内容：\n\n{resume_text}"
            }
        ]
        result = await AIService._chat(messages, temperature=0.3)
        return AIService._extract_json(result)

    @staticmethod
    async def analyze_resume(parsed_resume: dict, target_position: str) -> dict:
        """分析简历质量，给出评分、优劣势和改进建议"""
        # 判断是否为实习岗位，调整评价标准
        is_intern = any(kw in target_position.lower() for kw in ["实习", "intern"])
        if is_intern:
            level_hint = (
                "【重要】目标岗位是实习岗位，候选人是在校学生，请严格按实习生标准评价。\n"
                "禁止事项：\n"
                "- 禁止在weaknesses中提及'缺少实习经验'、'缺少工作经验'、'没有实际工作经验'等类似表述\n"
                "- 禁止因为项目是个人项目或校内项目而扣分，这对实习生来说是正常的\n"
                "- 禁止要求候选人具备线上生产环境经验\n"
                "评价重点：技术基础扎实度、项目完成度和技术深度、学习能力、编码能力。\n"
                "个人项目和校内项目同样能体现技术能力，请公正评价项目质量本身。\n"
            )
        else:
            level_hint = (
                "目标岗位是正式岗位，请按社招标准评价。\n"
                "重点关注：工作经验、项目深度、技术广度、解决复杂问题的能力。\n"
            )
        messages = [
            {
                "role": "system",
                "content": (
                    f"你是一个资深HR和职业规划师，请针对{target_position}岗位分析这份简历。\n"
                    f"{level_hint}"
                    "必须返回纯JSON格式（不要markdown代码块），包含以下字段：\n"
                    '{"overall_score": 7.5, '
                    '"strengths": ["优势1", "优势2", "优势3"], '
                    '"weaknesses": ["不足1", "不足2", "不足3"], '
                    '"suggestions": ["具体改进建议1", "具体改进建议2", "具体改进建议3"], '
                    '"keyword_match": ["匹配的关键技能1", "匹配的关键技能2"], '
                    '"missing_keywords": ["缺少的关键技能1", "缺少的关键技能2"], '
                    '"summary": "一段话总结简历质量和改进方向，100字以内"}'
                    "\n评分标准：9-10优秀，7-8良好，5-6一般，3-4较差，1-2很差"
                )
            },
            {
                "role": "user",
                "content": (
                    f"目标岗位：{target_position}\n"
                    f"简历内容：{json.dumps(parsed_resume, ensure_ascii=False)}"
                )
            }
        ]
        result = await AIService._chat(messages, temperature=0.4)
        return AIService._extract_json(result)

    @staticmethod
    async def generate_questions(
        parsed_resume: dict,
        target_position: str,
        difficulty: str,
        count: int
    ) -> list:
        """根据简历和目标岗位生成面试题目"""
        difficulty_map = {
            "easy": "初级，侧重基础知识和简单项目经验",
            "medium": "中级，涵盖技术深度和项目设计思路",
            "hard": "高级，深入系统设计、性能优化和技术原理"
        }
        difficulty_desc = difficulty_map.get(difficulty, difficulty_map["medium"])

        # 根据岗位名称判断是实习还是正式岗位，调整出题策略
        is_intern = any(kw in target_position for kw in ["实习", "intern", "Intern"])
        position_hint = ""
        if is_intern:
            position_hint = (
                "\n注意：这是实习岗位面试，候选人可能是在校学生，请适当降低难度：\n"
                "- 侧重基础知识（语言基础、数据结构、常用框架）\n"
                "- 项目经验题以学习过程和思路为主，不要求生产级方案\n"
                "- 不要出过于深入的系统设计和高并发优化题\n"
                "- 可以考察学习能力和成长潜力\n"
            )
        else:
            position_hint = (
                "\n注意：这是正式岗位面试，请按正常标准出题：\n"
                "- 要求候选人有扎实的技术基础和实际项目经验\n"
                "- 可以涉及系统设计、性能优化、线上问题排查等\n"
                "- 考察解决实际问题的能力和技术深度\n"
            )

        messages = [
            {
                "role": "system",
                "content": (
                    f"你是一个资深技术面试官，正在面试{target_position}岗位。\n"
                    f"面试难度：{difficulty_desc}\n"
                    f"{position_hint}\n"
                    "请根据候选人背景生成面试题。要求：\n"
                    "1. 结合候选人的项目经验和技术栈提问\n"
                    "2. 第一题是自我介绍\n"
                    "3. 覆盖技术深度、项目经验、基础知识\n"
                    "4. 返回纯JSON数组格式（不要markdown代码块）\n"
                    '格式：[{"index": 0, "question": "题目内容", "category": "分类"}]\n'
                    "分类包括：self-intro, project, technical, coding, system-design"
                )
            },
            {
                "role": "user",
                "content": (
                    f"候选人简历信息：{json.dumps(parsed_resume, ensure_ascii=False)}\n"
                    f"目标岗位：{target_position}\n"
                    f"请生成{count}道面试题。"
                )
            }
        ]
        result = await AIService._chat(messages, temperature=0.7)
        return AIService._extract_json(result)

    @staticmethod
    async def evaluate_answer(
        question: str,
        answer: str,
        resume_context: dict,
        chat_history: list,
        next_question: Optional[str] = None,
        reference_answer: Optional[str] = None,
        key_points: Optional[list] = None,
    ) -> dict:
        """评估候选人的回答，返回评分和反馈

        支持传入题库中的 reference_answer / key_points 作为评分参考依据，
        让 AI 评分有据可依、减少幻觉。
        """
        history_text = ""
        for msg in chat_history[-6:]:  # 保留最近6条消息，控制 token 用量
            role = "面试官" if msg["role"] == "interviewer" else "候选人"
            history_text += f"{role}: {msg['content']}\n"

        ref_block = ""
        if reference_answer:
            ref_block += f"\n【参考答案要点（评分依据，不要直接读给候选人）】：\n{reference_answer}\n"
        if key_points:
            ref_block += f"\n【关键采分点】：{json.dumps(key_points, ensure_ascii=False)}\n"

        messages = [
            {
                "role": "system",
                "content": (
                    "你是一个资深技术面试官，正在评估候选人的回答。\n"
                    + ("评分时请对照【参考答案要点】，候选人答中要点越多分越高。\n" if ref_block else "")
                    + "请返回纯JSON格式（不要markdown代码块）：\n"
                    '{"score": 7.5, "feedback": "简短反馈50字以内", '
                    '"follow_up": false}\n'
                    "评分标准：\n"
                    "- 9-10: 回答非常出色，有深度有见解\n"
                    "- 7-8: 回答良好，基本正确\n"
                    "- 5-6: 回答一般，有明显不足\n"
                    "- 3-4: 回答较差，理解有误\n"
                    "- 1-2: 基本没有回答到点上"
                )
            },
            {
                "role": "user",
                "content": (
                    f"候选人背景：{json.dumps(resume_context, ensure_ascii=False)}\n"
                    f"对话历史：\n{history_text}\n"
                    f"当前问题：{question}\n"
                    f"{ref_block}"
                    f"候选人回答：{answer}\n"
                    "请评估这个回答。"
                )
            }
        ]
        result = await AIService._chat(messages, temperature=0.5)
        return AIService._extract_json(result)

    @staticmethod
    async def evaluate_answer_stream(
        question: str,
        answer: str,
        resume_context: dict,
        chat_history: list,
        reference_answer: Optional[str] = None,
        key_points: Optional[list] = None,
    ):
        """流式版本：评估回答并逐块输出评语，最后输出 JSON 评分"""
        history_text = ""
        for msg in chat_history[-6:]:
            role = "面试官" if msg["role"] == "interviewer" else "候选人"
            history_text += f"{role}: {msg['content']}\n"

        ref_block = ""
        if reference_answer:
            ref_block += f"\n【参考答案要点（评分依据）】：\n{reference_answer}\n"
        if key_points:
            ref_block += f"\n【关键采分点】：{json.dumps(key_points, ensure_ascii=False)}\n"

        messages = [
            {
                "role": "system",
                "content": (
                    "你是一个资深技术面试官，正在评估候选人的回答。\n"
                    + ("评分时请对照【参考答案要点】，候选人答中要点越多分越高。\n" if ref_block else "")
                    + "请先用自然语言给出详细点评（100字左右），然后换行输出评分JSON。\n"
                    "格式要求：\n"
                    "先输出点评文字，然后另起一行输出：\n"
                    '```json\n{"score": 7.5}\n```'
                )
            },
            {
                "role": "user",
                "content": (
                    f"候选人背景：{json.dumps(resume_context, ensure_ascii=False)}\n"
                    f"对话历史：\n{history_text}\n"
                    f"当前问题：{question}\n"
                    f"{ref_block}"
                    f"候选人回答：{answer}\n"
                    "请评估这个回答。"
                )
            }
        ]
        async for chunk in AIService._chat_stream(messages, temperature=0.5):
            yield chunk

    # ── RAG 出题方法 ──────────────────────────────────────────────────

    @staticmethod
    async def select_and_adapt_questions(
        candidates: list,
        parsed_resume: dict,
        target_position: str,
        difficulty: str,
        target_n: int,
    ) -> list:
        """
        题库召回充分时调用：从候选题中挑 N 题，按难度递进排序，
        必要时基于候选人项目经验微调措辞（不改变题目本质）。
        每条返回保留 bank_id 和 reference_answer，标记 source=from_bank。
        """
        is_intern = any(kw in target_position for kw in ["实习", "intern", "Intern"])
        intern_hint = "候选人是在校学生（实习岗位），请优先选择基础类、项目类问题。" if is_intern else ""

        messages = [
            {
                "role": "system",
                "content": (
                    f"你是资深技术面试官，正在为【{target_position}】岗位选题。\n"
                    f"难度：{difficulty}。{intern_hint}\n\n"
                    f"我会提供 {len(candidates)} 道候选题（来自题库，按相似度排序）。\n"
                    f"你的任务：从中挑选 {target_n} 道作为最终面试题。\n"
                    "要求：\n"
                    "1. 第 1 题固定为自我介绍（如候选题里没有合适的，可以微调"
                    "   一道相关题作为开场）\n"
                    "2. 优先选与候选人简历项目/技能高度相关的题\n"
                    "3. 难度由浅入深排序\n"
                    "4. 可以微调措辞（如把 '介绍下你的高并发经验' 改成 '在你简历"
                    "   里那个订单系统项目，是怎么应对秒杀场景的'），但不要改变题目本质\n"
                    "5. **必须保留每道题原始的 id 字段，作为 bank_id 返回**\n"
                    "6. 返回纯 JSON 数组（不要 markdown 代码块）：\n"
                    '[{"index": 0, "question": "题面（可微调）", '
                    '"category": "self-intro/project/technical/coding/system-design", '
                    '"bank_id": <候选题的id>, '
                    '"reference_answer": <对应候选题的reference_answer>, '
                    '"source": "from_bank"}, ...]'
                )
            },
            {
                "role": "user",
                "content": (
                    f"候选人简历：{json.dumps(parsed_resume, ensure_ascii=False)}\n\n"
                    f"题库候选（{len(candidates)} 道）：\n"
                    f"{json.dumps(candidates, ensure_ascii=False)}\n\n"
                    f"请挑出最合适的 {target_n} 道题。"
                )
            }
        ]
        result = await AIService._chat(messages, temperature=0.3)
        return AIService._extract_json(result)

    @staticmethod
    async def generate_with_seeds(
        seed_questions: list,
        parsed_resume: dict,
        target_position: str,
        difficulty: str,
        target_n: int,
    ) -> list:
        """
        题库召回不足时调用：以题库题作为种子（必须保留），
        AI 兜底生成剩余的题，风格与种子题保持一致。
        """
        seed_count = len(seed_questions)
        fallback_count = target_n - seed_count

        is_intern = any(kw in target_position for kw in ["实习", "intern", "Intern"])
        intern_hint = "（实习岗位，候选人为在校学生，难度偏基础）" if is_intern else ""

        messages = [
            {
                "role": "system",
                "content": (
                    f"你是资深技术面试官，正在为【{target_position}】{intern_hint}岗位准备面试题。\n"
                    f"难度：{difficulty}\n\n"
                    f"已有 {seed_count} 道题来自题库（必须全部保留，可微调措辞），\n"
                    f"现在需要你再补 {fallback_count} 道高质量题，凑齐共 {target_n} 道。\n\n"
                    "要求：\n"
                    "1. 第 1 题固定为自我介绍\n"
                    "2. 题库题保留 bank_id 和 reference_answer 字段，source 标为 'from_bank'\n"
                    "3. 新生成的题 bank_id 留空（null），reference_answer 由你写一段标准答案要点，"
                    "   source 标为 'ai_fallback'\n"
                    "4. 整体难度递进（易→难）\n"
                    "5. 风格与题库题保持一致，避免太开放或与简历无关\n"
                    "6. 返回纯 JSON 数组（不要 markdown 代码块）：\n"
                    '[{"index": 0, "question": "...", "category": "self-intro/project/technical/coding/system-design", '
                    '"bank_id": null, "reference_answer": "...", "source": "ai_fallback"}, ...]'
                )
            },
            {
                "role": "user",
                "content": (
                    f"候选人简历：{json.dumps(parsed_resume, ensure_ascii=False)}\n\n"
                    f"题库种子题（{seed_count} 道）：\n"
                    f"{json.dumps(seed_questions, ensure_ascii=False)}\n\n"
                    f"请生成完整的 {target_n} 道题。"
                )
            }
        ]
        result = await AIService._chat(messages, temperature=0.5)
        return AIService._extract_json(result)

    @staticmethod
    async def generate_report(
        parsed_resume: dict,
        target_position: str,
        questions_and_scores: list
    ) -> dict:
        """根据面试记录生成综合评估报告"""
        qa_text = ""
        for item in questions_and_scores:
            qa_text += (
                f"问题：{item['question']}\n"
                f"回答：{item.get('answer', '未回答')}\n"
                f"得分：{item.get('score', 'N/A')}\n\n"
            )

        messages = [
            {
                "role": "system",
                "content": (
                    "你是一个资深技术面试官，请根据面试记录生成综合评估报告。\n"
                    "返回纯JSON格式（不要markdown代码块）：\n"
                    '{"summary": "总体评价100字以内", '
                    '"strengths": ["优势1", "优势2"], '
                    '"weaknesses": ["不足1", "不足2"], '
                    '"suggestions": ["建议1", "建议2"], '
                    '"hire_recommendation": "建议录用/待定/不建议录用"}'
                )
            },
            {
                "role": "user",
                "content": (
                    f"候选人背景：{json.dumps(parsed_resume, ensure_ascii=False)}\n"
                    f"目标岗位：{target_position}\n"
                    f"面试记录：\n{qa_text}\n"
                    "请生成综合评估报告。"
                )
            }
        ]
        result = await AIService._chat(messages, temperature=0.5)
        return AIService._extract_json(result)
