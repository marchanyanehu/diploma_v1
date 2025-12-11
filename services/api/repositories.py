"""
Repository layer for API service to keep persistence concerns isolated.
"""

from typing import Optional, Iterable, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from shared.database import User, ScrapingTask, ParserCache, ScheduledJob, Domain
from .schemas import TaskStatus


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_username(self, username: str) -> Optional[User]:
        return self.db.query(User).filter(User.username == username).first()

    def create(self, username: str, password_hash: str, email: Optional[str]) -> User:
        user = User(username=username, hashed_password=password_hash, email=email)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user


class TaskRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        task_id: str,
        url: str,
        user_prompt: str,
        status: str = TaskStatus.PENDING,
        owner_id: Optional[int] = None,
    ) -> ScrapingTask:
        task = ScrapingTask(
            task_id=task_id,
            url=url,
            user_prompt=user_prompt,
            status=status,
            owner_id=owner_id,
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def get_by_task_id(self, task_id: str) -> Optional[ScrapingTask]:
        return self.db.query(ScrapingTask).filter(ScrapingTask.task_id == task_id).first()

    def list_for_owner(self, owner_id: int, limit: int = 100) -> List[ScrapingTask]:
        """Return recent tasks for a specific user."""
        return (
            self.db.query(ScrapingTask)
            .filter(ScrapingTask.owner_id == owner_id)
            .order_by(ScrapingTask.created_at.desc())
            .limit(limit)
            .all()
        )


class ParserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def find_cached_parser(
        self,
        domain: str,
        keywords: Iterable[str] | None = None,
        confidence_threshold: int = 70,
        limit: int = 3,
    ) -> List[ParserCache]:
        # Use domain join for normalized schema
        q = (
            self.db.query(ParserCache)
            .join(Domain, ParserCache.domain_id == Domain.id)
            .filter(
                Domain.name == domain,
                ParserCache.confidence_score >= confidence_threshold,
                ParserCache.is_active == True,  # noqa: E712
            )
            .order_by(ParserCache.confidence_score.desc(), ParserCache.last_used_at.desc().nullslast())
        )
        parsers = list(q.limit(limit))
        if keywords:
            kw_low = {k.lower() for k in keywords if k}
            scored: List[tuple[int, int, ParserCache]] = []
            for p in parsers:
                p_kws = {k.lower() for k in (p.keyword_set or p.intent_keywords or [])}
                overlap = len(kw_low & p_kws)
                jacc = int((overlap / len(p_kws)) * 1000) if p_kws else 0
                scored.append((overlap, jacc, p))
            scored.sort(key=lambda t: (-t[0], -t[1], -t[2].confidence_score))
            filtered = [p for ov, _, p in scored if ov > 0]
            return filtered or [p for _, _, p in scored]
        return parsers


class ScheduleRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, url: str, prompt: str, cron: str, owner_id: int) -> ScheduledJob:
        job = ScheduledJob(url=url, prompt=prompt, schedule_cron=cron, owner_id=owner_id)
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def list_for_owner(self, owner_id: int) -> List[ScheduledJob]:
        return self.db.query(ScheduledJob).filter(ScheduledJob.owner_id == owner_id).all()

    def delete_for_owner(self, job_id: int, owner_id: int) -> bool:
        job = self.db.query(ScheduledJob).filter(ScheduledJob.id == job_id, ScheduledJob.owner_id == owner_id).first()
        if job:
            self.db.delete(job)
            self.db.commit()
            return True
        return False

