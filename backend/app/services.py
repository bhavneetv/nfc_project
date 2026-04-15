import json
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from pywebpush import WebPushException, webpush
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from .config import settings
from .models import PcAction, PcDevice, PushSubscription, Session as SessionModel, Streak, User


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def ensure_user(db: Session, user_id: str) -> None:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        db.add(User(id=user_id))
        db.flush()

    streak = db.query(Streak).filter(Streak.user_id == user_id).first()
    if not streak:
        db.add(Streak(user_id=user_id, current_streak=0, best_streak=0, last_active_date=None))
        db.flush()


def get_active_session(db: Session, user_id: str) -> Optional[SessionModel]:
    return (
        db.query(SessionModel)
        .filter(and_(SessionModel.user_id == user_id, SessionModel.end_time.is_(None)))
        .order_by(SessionModel.start_time.desc())
        .first()
    )


def update_streak_on_start(db: Session, user_id: str) -> Streak:
    streak = db.query(Streak).filter(Streak.user_id == user_id).first()
    today = date.today()

    if streak.last_active_date is None:
        streak.current_streak = 1
    else:
        delta_days = (today - streak.last_active_date).days
        if delta_days == 0:
            pass
        elif delta_days == 1:
            streak.current_streak += 1
        else:
            streak.current_streak = 1

    streak.last_active_date = today
    streak.best_streak = max(streak.best_streak, streak.current_streak)
    db.flush()
    return streak


def start_session(db: Session, user_id: str, mode: str, device_status: str) -> SessionModel:
    ensure_user(db, user_id)

    active = get_active_session(db, user_id)
    if active:
        return active

    update_streak_on_start(db, user_id)

    new_session = SessionModel(
        user_id=user_id,
        mode=mode,
        start_time=now_utc(),
        end_time=None,
        duration_seconds=None,
        device_status=device_status,
    )
    db.add(new_session)

    # Queue action for PC listener.
    action_payload = {
        "mode": mode,
        "open": {
            "study": ["youtube"],
            "coding": ["vscode", "spotify", "edge"],
            "fun": ["youtube", "netflix", "edge"],
        }[mode],
    }
    db.add(PcAction(user_id=user_id, mode=mode, payload=action_payload, status="pending"))

    db.flush()
    return new_session


def stop_session(db: Session, user_id: str, device_status: str) -> Optional[SessionModel]:
    active = get_active_session(db, user_id)
    if not active:
        return None

    end_time = now_utc()
    active.end_time = end_time
    active.duration_seconds = int((end_time - active.start_time).total_seconds())
    active.device_status = device_status
    db.flush()
    return active


def to_session_dict(session: SessionModel) -> dict:
    return {
        "id": session.id,
        "mode": session.mode,
        "start_time": session.start_time,
        "end_time": session.end_time,
        "duration_seconds": session.duration_seconds,
        "device_status": session.device_status,
    }


def get_last_7_days_breakdown(db: Session, user_id: str) -> list:
    today = date.today()
    rows = (
        db.query(
            func.date(SessionModel.start_time).label("day"),
            func.coalesce(func.sum(SessionModel.duration_seconds), 0).label("seconds"),
        )
        .filter(
            SessionModel.user_id == user_id,
            SessionModel.end_time.is_not(None),
            SessionModel.start_time >= datetime.combine(today - timedelta(days=6), datetime.min.time()),
        )
        .group_by(func.date(SessionModel.start_time))
        .all()
    )

    by_day = {str(row.day): int(row.seconds or 0) for row in rows}
    output = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        output.append({"date": str(day), "total_seconds": by_day.get(str(day), 0)})
    return output


def send_push_to_user(db: Session, user_id: str, title: str, body: str, extra: Optional[dict] = None) -> int:
    if not settings.vapid_private_key or not settings.vapid_public_key:
        return 0

    subscriptions = db.query(PushSubscription).filter(PushSubscription.user_id == user_id).all()
    if not subscriptions:
        return 0

    payload = json.dumps(
        {
            "title": title,
            "body": body,
            "url": settings.public_base_url + "/select.html",
            "extra": extra or {},
        }
    )

    sent_count = 0
    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                },
                data=payload,
                vapid_private_key=settings.vapid_private_key,
                vapid_claims={"sub": settings.vapid_subject},
            )
            sent_count += 1
        except WebPushException:
            db.delete(sub)
    db.flush()
    return sent_count


def upsert_pc_status(db: Session, device_id: str, user_id: str, status: str) -> None:
    ensure_user(db, user_id)
    existing = db.query(PcDevice).filter(PcDevice.id == device_id).first()
    if not existing:
        db.add(
            PcDevice(
                id=device_id,
                user_id=user_id,
                status=status,
                last_seen=now_utc(),
                updated_at=now_utc(),
            )
        )
        db.flush()
        return

    existing.user_id = user_id
    existing.status = status
    existing.last_seen = now_utc()
    existing.updated_at = now_utc()
    db.flush()
