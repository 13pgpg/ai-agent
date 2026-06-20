"""
导入岗位模板初始数据。

用法（在 VM 容器里）：
    sudo docker exec -it ai-interview-app python scripts/seed_position_templates.py
"""
import asyncio
from sqlalchemy import select
from app.db.base import get_session_local
from app.models.position_template import PositionTemplate


SEED_POSITIONS = [
    {
        "position_tag": "python_backend",
        "title": "Python 后端开发工程师",
        "category": "backend",
        "level": "junior",
        "core_skills": ["Python", "FastAPI/Django/Flask", "MySQL", "Redis", "Linux", "Git"],
        "nice_to_have_skills": ["消息队列", "Docker", "微服务", "Kubernetes"],
        "project_keywords": ["电商系统", "RESTful API", "高并发", "缓存优化", "AI 应用"],
        "focus_topics": ["Python 基础", "并发与协程", "Redis 缓存", "MySQL 索引", "FastAPI 实践"],
        "recommended_query_keywords": ["python_backend", "Python", "Redis", "asyncio", "FastAPI", "MySQL"],
        "recommended_difficulty": "medium",
        "recommended_question_count": 8,
        "jd_summary": "负责后端服务开发，要求扎实的 Python 基础、熟悉常用框架与数据库，有良好的工程素养。",
        "typical_companies": ["小型互联网公司", "AI 应用方向初创", "中型 SaaS 公司"],
        "sort_order": 1,
    },
    {
        "position_tag": "java_backend",
        "title": "Java 后端开发工程师",
        "category": "backend",
        "level": "junior",
        "core_skills": ["Java", "Spring Boot", "MyBatis", "MySQL", "Redis", "Maven"],
        "nice_to_have_skills": ["Spring Cloud", "Dubbo", "Kafka", "Docker"],
        "project_keywords": ["电商系统", "微服务", "高并发", "分布式"],
        "focus_topics": ["Java 基础", "JVM", "Spring 原理", "MySQL", "Redis", "并发编程"],
        "recommended_query_keywords": ["java_backend", "Java", "Spring", "MySQL", "JVM", "并发"],
        "recommended_difficulty": "medium",
        "recommended_question_count": 8,
        "jd_summary": "负责 Java 后端业务系统开发，要求熟悉 Spring 全家桶、JVM 调优、并发编程。",
        "typical_companies": ["大中型互联网公司", "传统行业 IT 部门"],
        "sort_order": 2,
    },
    {
        "position_tag": "vue_frontend",
        "title": "Vue 前端开发工程师",
        "category": "frontend",
        "level": "junior",
        "core_skills": ["Vue 3", "JavaScript/TypeScript", "Vite", "Pinia", "HTML/CSS"],
        "nice_to_have_skills": ["Element Plus", "Tailwind CSS", "SSR / Nuxt", "WebSocket"],
        "project_keywords": ["管理后台", "B 端系统", "小程序", "数据可视化"],
        "focus_topics": ["Vue 3 响应式原理", "组合式 API", "路由", "状态管理", "性能优化"],
        "recommended_query_keywords": ["vue_frontend", "Vue", "Vite", "Pinia", "JavaScript", "前端"],
        "recommended_difficulty": "medium",
        "recommended_question_count": 7,
        "jd_summary": "负责 Web 前端页面开发，熟悉 Vue 3 生态，能独立完成中型业务模块。",
        "typical_companies": ["B 端 SaaS 公司", "中小互联网"],
        "sort_order": 3,
    },
    {
        "position_tag": "react_frontend",
        "title": "React 前端开发工程师",
        "category": "frontend",
        "level": "junior",
        "core_skills": ["React", "JavaScript/TypeScript", "Webpack/Vite", "Redux/Zustand", "HTML/CSS"],
        "nice_to_have_skills": ["Next.js", "Tailwind CSS", "React Query", "WebSocket"],
        "project_keywords": ["B 端管理系统", "C 端业务", "Hybrid App"],
        "focus_topics": ["React Hooks", "状态管理", "性能优化", "TypeScript", "工程化"],
        "recommended_query_keywords": ["react_frontend", "React", "Hooks", "TypeScript", "Webpack"],
        "recommended_difficulty": "medium",
        "recommended_question_count": 7,
        "jd_summary": "负责 React 前端业务开发，熟悉 Hooks、状态管理与工程化体系。",
        "typical_companies": ["互联网大厂", "外企", "AI 应用前端"],
        "sort_order": 4,
    },
    {
        "position_tag": "ai_application",
        "title": "AI 应用开发工程师",
        "category": "ai",
        "level": "junior",
        "core_skills": ["Python", "LangChain", "RAG", "Prompt 工程", "向量数据库", "FastAPI"],
        "nice_to_have_skills": ["Agent 框架", "Fine-tuning", "Embedding 模型", "Streamlit"],
        "project_keywords": ["智能客服", "知识库问答", "AI 助手", "RAG 系统", "Agent"],
        "focus_topics": ["LLM 调用", "RAG 架构", "Prompt 设计", "向量检索", "Agent 工作流"],
        "recommended_query_keywords": ["ai_application", "RAG", "LangChain", "Embedding", "向量", "Prompt"],
        "recommended_difficulty": "medium",
        "recommended_question_count": 7,
        "jd_summary": "负责基于大模型的 AI 应用开发，包含 RAG 系统、Agent、Prompt 工程等。",
        "typical_companies": ["AI 创业公司", "互联网大厂 AI 部门", "传统行业智能化转型"],
        "sort_order": 5,
    },
    {
        "position_tag": "fullstack",
        "title": "全栈开发工程师",
        "category": "backend",
        "level": "junior",
        "core_skills": ["Python/Node.js", "Vue/React", "MySQL", "Redis", "Docker"],
        "nice_to_have_skills": ["微服务", "Nginx", "CI/CD"],
        "project_keywords": ["独立项目", "MVP 产品", "中型 Web 应用"],
        "focus_topics": ["前后端协作", "数据库设计", "性能优化", "部署运维"],
        "recommended_query_keywords": ["fullstack", "全栈", "Python", "Vue", "MySQL"],
        "recommended_difficulty": "medium",
        "recommended_question_count": 8,
        "jd_summary": "独立完成前后端开发，适合中小公司或初创团队。",
        "typical_companies": ["初创公司", "外包公司", "小型团队"],
        "sort_order": 6,
    },
    {
        "position_tag": "mobile_android",
        "title": "Android 开发工程师",
        "category": "mobile",
        "level": "junior",
        "core_skills": ["Kotlin/Java", "Android SDK", "Jetpack Compose", "Room", "Retrofit"],
        "nice_to_have_skills": ["NDK", "Flutter", "性能优化"],
        "project_keywords": ["商业 App", "工具类 App", "音视频"],
        "focus_topics": ["Android 四大组件", "性能优化", "内存管理", "Compose UI"],
        "recommended_query_keywords": ["android", "Kotlin", "Jetpack", "Compose"],
        "recommended_difficulty": "medium",
        "recommended_question_count": 7,
        "jd_summary": "负责 Android 端业务开发，熟悉 Jetpack 全家桶和性能优化。",
        "typical_companies": ["互联网公司 App 端", "音视频公司"],
        "sort_order": 7,
    },
    {
        "position_tag": "devops",
        "title": "DevOps / 运维工程师",
        "category": "devops",
        "level": "junior",
        "core_skills": ["Linux", "Shell", "Docker", "Kubernetes", "CI/CD", "监控"],
        "nice_to_have_skills": ["Terraform", "Ansible", "Prometheus", "ELK"],
        "project_keywords": ["容器化", "自动化部署", "监控告警", "高可用"],
        "focus_topics": ["Linux 运维", "K8s 架构", "CI/CD 设计", "监控体系"],
        "recommended_query_keywords": ["devops", "Linux", "Docker", "Kubernetes", "CI/CD"],
        "recommended_difficulty": "medium",
        "recommended_question_count": 7,
        "jd_summary": "负责服务的部署、监控与稳定性保障，搭建 CI/CD 流水线。",
        "typical_companies": ["互联网中台部门", "云服务提供商"],
        "sort_order": 8,
    },
]


async def main():
    """检查 → 已存在则跳过 → 不存在则插入"""
    AsyncSessionLocal = get_session_local()
    async with AsyncSessionLocal() as db:
        inserted = 0
        skipped = 0
        for item in SEED_POSITIONS:
            tag = item["position_tag"]
            existing = (await db.execute(
                select(PositionTemplate).where(PositionTemplate.position_tag == tag)
            )).scalar_one_or_none()
            if existing:
                print(f"  [跳过] {tag} 已存在")
                skipped += 1
                continue
            db.add(PositionTemplate(**item))
            print(f"  [新增] {tag} - {item['title']}")
            inserted += 1
        await db.commit()
        print(f"\n种子数据完成：新增 {inserted} 条，跳过 {skipped} 条")


if __name__ == "__main__":
    asyncio.run(main())
