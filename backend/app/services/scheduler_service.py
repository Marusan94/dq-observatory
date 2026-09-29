"""Scheduled jobs and webhook notifications for automated quality monitoring."""
import json
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from sqlalchemy import Column, String, DateTime, Text, Integer, Boolean
from sqlalchemy.orm import Session
from app.models.base import Base
import httpx
import croniter
import threading
import time


class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    DISABLED = "DISABLED"
    PAUSED = "PAUSED"


class WebhookEvent(str, Enum):
    QUALITY_RUN_COMPLETED = "quality_run_completed"
    QUALITY_SCORE_DROPPED = "quality_score_dropped"
    DRIFT_DETECTED = "drift_detected"
    ISSUES_THRESHOLD_EXCEEDED = "issues_threshold_exceeded"
    JOB_FAILED = "job_failed"


class ScheduledJob(Base):
    __tablename__ = "scheduled_jobs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    cron_expression = Column(String, nullable=False)  # e.g., "0 2 * * *" for daily 2am
    dataset_id = Column(String, nullable=True)  # None = all datasets
    ruleset = Column(String, default="general-v1")
    config = Column(Text, default="{}")  # JSON config
    status = Column(String, default=JobStatus.PENDING.value)
    last_run = Column(DateTime, nullable=True)
    next_run = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    enabled = Column(Boolean, default=True)
    max_retries = Column(Integer, default=3)
    timeout_seconds = Column(Integer, default=3600)


class Webhook(Base):
    __tablename__ = "webhooks"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    secret = Column(String, default="")  # For HMAC signing
    events = Column(Text, default="[]")  # JSON array of WebhookEvent values
    headers = Column(Text, default="{}")  # Additional headers
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_triggered = Column(DateTime, nullable=True)
    failure_count = Column(Integer, default=0)


class JobRun(Base):
    __tablename__ = "job_runs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String, nullable=False, index=True)
    dataset_id = Column(String, nullable=True)
    status = Column(String, default=JobStatus.PENDING.value)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, default=0)
    quality_score = Column(Text, default="{}")
    issues_found = Column(Integer, default=0)
    error_message = Column(Text, default="")
    triggered_by = Column(String, default="scheduled")  # scheduled, manual, webhook


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    webhook_id = Column(String, nullable=False, index=True)
    event = Column(String, nullable=False)
    payload = Column(Text, default="{}")
    response_status = Column(Integer, default=0)
    response_body = Column(Text, default="")
    attempt = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    delivered_at = Column(DateTime, nullable=True)


class JobScheduler:
    """Background job scheduler with cron support."""
    
    def __init__(self, db_factory: Callable[[], Session], check_interval: int = 60):
        self.db_factory = db_factory
        self.check_interval = check_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._job_handlers: Dict[str, Callable] = {}
    
    def register_handler(self, job_type: str, handler: Callable):
        self._job_handlers[job_type] = handler
    
    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
    
    def pause_job(self, job_id: str) -> bool:
        """Pause a scheduled job."""
        db = self.db_factory()
        try:
            job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()
            if job and job.status != JobStatus.PAUSED.value:
                job.status = JobStatus.PAUSED.value
                job.updated_at = datetime.utcnow()
                db.commit()
                return True
            return False
        finally:
            db.close()
    
    def resume_job(self, job_id: str) -> bool:
        """Resume a paused scheduled job."""
        db = self.db_factory()
        try:
            job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()
            if job and job.status == JobStatus.PAUSED.value:
                job.status = JobStatus.PENDING.value
                # Recalculate next run
                cron = croniter.croniter(job.cron_expression, datetime.utcnow())
                job.next_run = cron.get_next(datetime)
                job.updated_at = datetime.utcnow()
                db.commit()
                return True
            return False
        finally:
            db.close()
    
    def _run_loop(self):
        while self._running:
            try:
                self._check_and_run_jobs()
            except Exception as e:
                print(f"Scheduler error: {e}")
            time.sleep(self.check_interval)
    
    def _check_and_run_jobs(self):
        db = self.db_factory()
        try:
            now = datetime.utcnow()
            jobs = db.query(ScheduledJob).filter(
                ScheduledJob.enabled == True,
                ScheduledJob.status != JobStatus.DISABLED.value,
                ScheduledJob.next_run <= now
            ).all()
            
            for job in jobs:
                self._execute_job(db, job)
                # Update next run
                cron = croniter.croniter(job.cron_expression, now)
                job.next_run = cron.get_next(datetime)
                job.updated_at = now
                db.commit()
        finally:
            db.close()
    
    def _execute_job(self, db: Session, job: ScheduledJob):
        run = JobRun(
            id=str(uuid.uuid4()),
            job_id=job.id,
            dataset_id=job.dataset_id,
            status=JobStatus.RUNNING.value,
            triggered_by="scheduled"
        )
        db.add(run)
        db.commit()
        
        t0 = time.time()
        try:
            handler = self._job_handlers.get("quality_run")
            if handler:
                result = handler(db, job)
                run.status = JobStatus.COMPLETED.value
                run.quality_score = json.dumps(result.get("score", {}))
                run.issues_found = result.get("issues_count", 0)
            else:
                run.status = JobStatus.FAILED.value
                run.error_message = "No handler registered for quality_run"
        except Exception as e:
            run.status = JobStatus.FAILED.value
            run.error_message = str(e)
        finally:
            run.completed_at = datetime.utcnow()
            run.duration_ms = int((time.time() - t0) * 1000)
            db.commit()
            
            # Trigger webhooks
            self._trigger_webhooks(db, job, run)
    
    def _trigger_webhooks(self, db: Session, job: ScheduledJob, run: JobRun):
        webhooks = db.query(Webhook).filter(Webhook.active == True).all()
        event = WebhookEvent.QUALITY_RUN_COMPLETED.value
        if run.status == JobStatus.FAILED.value:
            event = WebhookEvent.JOB_FAILED.value
        
        payload = {
            "event": event,
            "job_id": job.id,
            "job_name": job.name,
            "run_id": run.id,
            "dataset_id": run.dataset_id,
            "status": run.status,
            "quality_score": json.loads(run.quality_score or "{}"),
            "issues_found": run.issues_found,
            "timestamp": run.completed_at.isoformat() if run.completed_at else None,
        }
        
        for webhook in webhooks:
            events = json.loads(webhook.events or "[]")
            if event in events:
                self._deliver_webhook(db, webhook, event, payload)
    
    def _deliver_webhook(self, db: Session, webhook: Webhook, event: str, payload: Dict):
        delivery = WebhookDelivery(
            id=str(uuid.uuid4()),
            webhook_id=webhook.id,
            event=event,
            payload=json.dumps(payload, default=str),
            attempt=1
        )
        db.add(delivery)
        db.commit()
        
        # Async delivery
        threading.Thread(target=self._send_webhook, args=(webhook, event, payload, delivery.id), daemon=True).start()
    
    def _send_webhook(self, webhook: Webhook, event: str, payload: Dict, delivery_id: str):
        import hmac
        import hashlib
        
        db = self.db_factory()
        try:
            headers = json.loads(webhook.headers or "{}")
            headers["Content-Type"] = "application/json"
            headers["X-DQ-Event"] = event
            headers["X-DQ-Delivery"] = delivery_id
            
            body = json.dumps(payload, default=str).encode()
            if webhook.secret:
                sig = hmac.new(webhook.secret.encode(), body, hashlib.sha256).hexdigest()
                headers["X-DQ-Signature"] = f"sha256={sig}"
            
            max_retries = 3
            base_delay = 5  # seconds
            
            for attempt in range(1, max_retries + 1):
                delivery = db.query(WebhookDelivery).filter(WebhookDelivery.id == delivery_id).first()
                if delivery:
                    delivery.attempt = attempt
                    db.commit()
                
                try:
                    with httpx.Client(timeout=30.0) as client:
                        resp = client.post(webhook.url, content=body, headers=headers)
                        delivery = db.query(WebhookDelivery).filter(WebhookDelivery.id == delivery_id).first()
                        if delivery:
                            delivery.response_status = resp.status_code
                            delivery.response_body = resp.text[:1000]
                            delivery.delivered_at = datetime.utcnow()
                            db.commit()
                            
                            # Update webhook stats
                            if resp.status_code >= 400:
                                webhook.failure_count += 1
                                # Retry on 4xx/5xx
                                if attempt < max_retries:
                                    delay = base_delay * (2 ** (attempt - 1))  # exponential backoff
                                    time.sleep(delay)
                                    continue
                            else:
                                webhook.failure_count = 0
                                webhook.last_triggered = datetime.utcnow()
                                db.commit()
                            break  # success or max retries reached
                except Exception as e:
                    delivery = db.query(WebhookDelivery).filter(WebhookDelivery.id == delivery_id).first()
                    if delivery:
                        delivery.response_status = 0
                        delivery.response_body = str(e)[:1000]
                        db.commit()
                    if attempt < max_retries:
                        delay = base_delay * (2 ** (attempt - 1))
                        time.sleep(delay)
                        continue
                    break
        finally:
            db.close()


def create_scheduler(db_factory: Callable[[], Session]) -> JobScheduler:
    """Factory function to create and configure scheduler."""
    scheduler = JobScheduler(db_factory)
    return scheduler