"""APScheduler background job — grievance deadline monitoring.

Runs daily at 08:00 local time alongside n8n Workflow 2.

The job:
  1. Queries all open/pending_arbitration grievances.
  2. For each grievance, checks step1_deadline, step2_deadline, and
     arbitration_deadline against today.
  3. If any deadline is within ALERT_WINDOW_DAYS (default 7), creates a
     GrievanceAlert row (avoiding duplicates for alerts already created today).
  4. Posts all new alerts to POST /api/v1/agents/checkin for the President
     agent so they surface in the morning context bundle.

The scheduler is started from app.py during FastAPI lifespan startup and
stopped cleanly on shutdown.
"""

from __future__ import annotations

import logging
import os
from datetime import date, datetime, timezone

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from integrations.pulse.core.business_days import days_until
from integrations.pulse.db.models.grievance import Grievance, GrievanceAlert
from integrations.pulse.db.session import SessionLocal

logger = logging.getLogger(__name__)

ALERT_WINDOW_DAYS: int = int(os.environ.get("GRIEVANCE_ALERT_WINDOW_DAYS", "7"))
PRESIDENT_AGENT_ID: str = os.environ.get("PRESIDENT_AGENT_ID", "dave-president")
PULSE_BASE_URL: str = os.environ.get("PULSE_BASE_URL", "http://localhost:8000")

# Internal service token for the scheduler's checkin POST (system action).
# In production this should be a long-lived service JWT; in dev it can be a
# placeholder accepted by dev-mode auth.
SCHEDULER_SERVICE_TOKEN: str = os.environ.get(
    "SCHEDULER_SERVICE_TOKEN", "dev-scheduler-token"
)

_OPEN_STATUSES = {"open", "pending_arbitration"}


async def _monitor_grievance_deadlines() -> None:
    """Core deadline monitoring logic — runs once per day."""
    today = date.today()
    logger.info("[scheduler] Grievance deadline scan starting — today is %s", today)

    db: Session = SessionLocal()
    new_alerts: list[dict] = []

    try:
        grievances = (
            db.query(Grievance)
            .filter(Grievance.status.in_(_OPEN_STATUSES))
            .all()
        )

        for g in grievances:
            for deadline_type, deadline_date in [
                ("step1", g.step1_deadline),
                ("step2", g.step2_deadline),
                ("arbitration", g.arbitration_deadline),
            ]:
                remaining = days_until(deadline_date, today)
                if remaining < 0 or remaining > ALERT_WINDOW_DAYS:
                    continue

                # Avoid duplicate alerts created on the same calendar day
                already_exists = (
                    db.query(GrievanceAlert)
                    .filter(
                        GrievanceAlert.grievance_id == g.id,
                        GrievanceAlert.deadline_type == deadline_type,
                        GrievanceAlert.created_at >= datetime.combine(today, datetime.min.time()),
                    )
                    .first()
                )
                if already_exists:
                    continue

                alert = GrievanceAlert(
                    grievance_id=g.id,
                    deadline_type=deadline_type,
                    days_remaining=remaining,
                )
                db.add(alert)
                db.flush()  # populate alert.id before appending

                new_alerts.append(
                    {
                        "alert_id": alert.id,
                        "case_number": g.case_number,
                        "facility": g.facility,
                        "deadline_type": deadline_type,
                        "days_remaining": remaining,
                        "status": g.status,
                    }
                )

        db.commit()
    except Exception:
        db.rollback()
        logger.exception("[scheduler] Error during deadline scan — rolled back")
        return
    finally:
        db.close()

    if not new_alerts:
        logger.info("[scheduler] No approaching deadlines found.")
        return

    logger.info("[scheduler] Created %d new deadline alert(s)", len(new_alerts))

    # Post alerts to the agent checkin endpoint
    await _post_alerts_to_checkin(new_alerts, today)


async def _post_alerts_to_checkin(
    alerts: list[dict],
    today: date,
) -> None:
    """Deliver deadline alerts to the President agent via /api/v1/agents/checkin."""
    payload = {
        "agent_id": PRESIDENT_AGENT_ID,
        "checkin_type": "morning",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": (
            f"Deadline monitor: {len(alerts)} grievance deadline(s) "
            f"approaching within {ALERT_WINDOW_DAYS} days."
        ),
        "alerts": [
            {
                "type": "deadline",
                "message": (
                    f"Grievance {a['case_number']} ({a['facility']}) — "
                    f"{a['deadline_type']} deadline in {a['days_remaining']} day(s)"
                ),
                "priority": "high" if a["days_remaining"] <= 2 else "medium",
            }
            for a in alerts
        ],
    }

    url = f"{PULSE_BASE_URL}/api/v1/agents/checkin"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {SCHEDULER_SERVICE_TOKEN}"},
            )
            resp.raise_for_status()

        # Mark each alert as posted
        db: Session = SessionLocal()
        try:
            alert_ids = [a["alert_id"] for a in alerts]
            db.query(GrievanceAlert).filter(
                GrievanceAlert.id.in_(alert_ids)
            ).update(
                {"posted_at": datetime.utcnow()},
                synchronize_session=False,
            )
            db.commit()
        finally:
            db.close()

        logger.info("[scheduler] Posted %d alert(s) to %s", len(alerts), url)

    except httpx.HTTPError as exc:
        logger.error("[scheduler] Failed to post alerts to checkin: %s", exc)


def create_scheduler() -> AsyncIOScheduler:
    """Create and configure the APScheduler instance.

    The scheduler is NOT started here — call ``scheduler.start()`` during
    FastAPI app lifespan startup.
    """
    scheduler = AsyncIOScheduler(timezone="America/New_York")

    # Daily at 08:00 ET — alongside n8n Workflow 2
    scheduler.add_job(
        _monitor_grievance_deadlines,
        trigger=CronTrigger(hour=8, minute=0, timezone="America/New_York"),
        id="grievance_deadline_monitor",
        name="Grievance Deadline Monitor",
        replace_existing=True,
        misfire_grace_time=3600,  # 1-hour grace window if job misfires
    )

    return scheduler
