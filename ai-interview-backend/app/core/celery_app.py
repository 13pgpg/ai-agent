import os
from celery import Celery
from app.core.config import settings

# 配置 Celery
celery_app = Celery(
    "tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        'app.schedule.celery_job',
        'app.schedule.jobs.demo',
        'app.schedule.jobs.email_tasks',
        'app.schedule.jobs.knowledge_tasks',  # 知识库 RAG 任务
    ]
)

# 配置 Celery Beat（定时任务）
celery_app.conf.beat_schedule = {
    'demo-every-minute': {
        'task': 'app.schedule.jobs.demo.execute',  # 更新为新的任务路径
        'schedule': 60.0,  # 每分钟执行
        'options': {'queue': 'scheduled_tasks'}
    },
}

celery_app.conf.timezone = 'UTC'
celery_app.conf.task_queues = {
    'scheduled_tasks': {
        'exchange': 'scheduled_tasks',
        'routing_key': 'scheduled_tasks',
    },
    'celery': {  # 默认队列
        'exchange': 'celery',
        'routing_key': 'celery',
    }
}

# Optional: Configure other Celery settings
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    task_track_started=True,
    worker_concurrency=os.cpu_count(),
    task_time_limit=30 * 60,  # 30 minutes time limit
    task_soft_time_limit=15 * 60,  # 15 minutes soft time limit
)