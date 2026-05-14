from __future__ import annotations

import json
from dataclasses import dataclass

import redis

from progrec_service.config import settings


def queue_name() -> str:
    return "pipeline-jobs"


@dataclass(frozen=True)
class QueueMessage:
    job_id: str


def redis_client() -> redis.Redis:
    return redis.Redis.from_url(settings.redis_url, decode_responses=True)


def encode_job_message(job_id: str) -> str:
    return json.dumps({"job_id": job_id})


def enqueue_job(job_id: str) -> None:
    redis_client().rpush(queue_name(), encode_job_message(job_id))
