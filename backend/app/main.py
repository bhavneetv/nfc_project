from datetime import datetime, timedelta
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import PcAction, PcDevice, PcSelectorRequest, Session as SessionModel, Streak
from .schemas import (
    PcAckRequest,
    PcSelectorAckRequest,
    PcHeartbeatRequest,
    StartRequest,
    StartStopResponse,
    StopRequest,
    SubscribeRequest,
    TapRequest,
    WeeklyResponse,
    WidgetResponse,
)
from .services import (
    ensure_user,
    get_active_session,
    get_last_7_days_breakdown,
    send_push_to_user,
    start_session,
    stop_session,
    to_session_dict,
    upsert_pc_status,
)

app = FastAPI(title="NFC Productivity Tracker", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


def _send_session_stopped_push(db: Session, user_id: str, session: SessionModel) -> None:
    duration_seconds = int(session.duration_seconds or 0)
    duration_minutes = max(1, int(duration_seconds / 60))

    mode_total_row = (
        db.query(func.coalesce(func.sum(SessionModel.duration_seconds), 0).label("s"))
        .filter(
            SessionModel.user_id == user_id,
            SessionModel.mode == session.mode,
            SessionModel.end_time.is_not(None),
        )
        .first()
    )
    mode_total_seconds = int(mode_total_row.s or 0)
    mode_total_minutes = max(1, int(mode_total_seconds / 60))

    send_push_to_user(
        db,
        user_id,
        "Session stopped",
        f"Duration: {duration_minutes} min ({session.mode}) | Total {session.mode}: {mode_total_minutes} min",
        {
            "duration_seconds": duration_seconds,
            "mode": session.mode,
            "mode_total_seconds": mode_total_seconds,
        },
    )


@app.get("/health")
def health_check():
    return {"ok": True, "service": "nfc-productivity-api"}


@app.get("/")
def root_redirect():
    return FileResponse(static_dir / "select.html")


@app.get("/select.html")
def select_page():
    return FileResponse(static_dir / "select.html")


@app.get("/logs.html")
def logs_page():
    return FileResponse(static_dir / "logs.html")


@app.get("/sw.js")
def service_worker_file():
    return FileResponse(static_dir / "sw.js")


@app.get("/api/config")
def get_config():
    return {"vapidPublicKey": settings.vapid_public_key, "defaultUserId": settings.default_user_id}


@app.post("/api/push/subscribe")
def push_subscribe(payload: SubscribeRequest, db: Session = Depends(get_db)):
    from .models import PushSubscription

    ensure_user(db, payload.user_id)
    p256dh = payload.keys.get("p256dh")
    auth = payload.keys.get("auth")
    if not p256dh or not auth:
        raise HTTPException(status_code=400, detail="Missing push subscription keys")

    existing = db.query(PushSubscription).filter(PushSubscription.endpoint == payload.endpoint).first()
    if existing:
        existing.user_id = payload.user_id
        existing.p256dh = p256dh
        existing.auth = auth
    else:
        db.add(
            PushSubscription(
                user_id=payload.user_id,
                endpoint=payload.endpoint,
                p256dh=p256dh,
                auth=auth,
            )
        )

    db.commit()
    return {"ok": True}


@app.post("/api/session/start", response_model=StartStopResponse)
def api_start(payload: StartRequest, db: Session = Depends(get_db)):
    session = start_session(db, payload.user_id, payload.mode, payload.device_status)
    db.commit()

    if payload.device_status == "pc_off":
        send_push_to_user(
            db,
            payload.user_id,
            "PC is OFF",
            f"Started {payload.mode} session, but PC is off.",
            {"mode": payload.mode},
        )
        db.commit()

    return {
        "action": "started",
        "session": to_session_dict(session),
        "message": f"Session started: {session.mode}",
    }


@app.post("/api/session/stop", response_model=StartStopResponse)
def api_stop(payload: StopRequest, db: Session = Depends(get_db)):
    session = stop_session(db, payload.user_id, payload.device_status)
    if not session:
        raise HTTPException(status_code=404, detail="No active session")

    db.commit()

    _send_session_stopped_push(db, payload.user_id, session)
    db.commit()

    return {
        "action": "stopped",
        "session": to_session_dict(session),
        "message": "Last event logged off",
    }


@app.post("/api/nfc/tap", response_model=StartStopResponse)
def api_nfc_tap(payload: TapRequest, db: Session = Depends(get_db)):
    return _handle_nfc_tap(payload.user_id, payload.mode, payload.device_status, db)


@app.get("/api/nfc/tap", response_model=StartStopResponse)
def api_nfc_tap_get(user_id: str, mode: str | None = None, device_status: str = "pc_on", db: Session = Depends(get_db)):
    return _handle_nfc_tap(user_id, mode, device_status, db)


def _handle_nfc_tap(user_id: str, mode: str | None, device_status: str, db: Session):
    active = get_active_session(db, user_id)
    if active:
        stopped = stop_session(db, user_id, device_status)
        db.commit()

        _send_session_stopped_push(db, user_id, stopped)
        db.commit()
        return {
            "action": "stopped",
            "session": to_session_dict(stopped),
            "message": "Last event logged off",
        }

    if not mode:
        raise HTTPException(status_code=400, detail="Mode required when starting session")

    started = start_session(db, user_id, mode, device_status)
    db.commit()

    if device_status == "pc_off":
        send_push_to_user(
            db,
            user_id,
            "PC is OFF",
            f"Started {mode} session, but PC is off.",
            {"mode": mode},
        )
        db.commit()

    return {
        "action": "started",
        "session": to_session_dict(started),
        "message": f"Session started: {started.mode}",
    }


def _get_latest_pc_status(user_id: str, db: Session) -> str:
    latest_device = (
        db.query(PcDevice)
        .filter(PcDevice.user_id == user_id)
        .order_by(PcDevice.last_seen.desc())
        .first()
    )
    if not latest_device:
        return "pc_off"

    last_seen = latest_device.last_seen
    if getattr(last_seen, "tzinfo", None) is not None:
        last_seen = last_seen.replace(tzinfo=None)
    age_seconds = (datetime.utcnow() - last_seen).total_seconds()
    if age_seconds > 20:
        return "pc_off"
    return latest_device.status


@app.get("/api/nfc/next-step")
def api_nfc_next_step(user_id: str, db: Session = Depends(get_db)):
    ensure_user(db, user_id)

    active = get_active_session(db, user_id)
    if active:
        return {"step": "stop", "reason": "active_session", "device_status": _get_latest_pc_status(user_id, db)}

    pc_status = _get_latest_pc_status(user_id, db)
    if pc_status == "pc_on":
        existing = (
            db.query(PcSelectorRequest)
            .filter(PcSelectorRequest.user_id == user_id, PcSelectorRequest.status == "pending")
            .order_by(PcSelectorRequest.created_at.asc())
            .first()
        )
        if not existing:
            db.add(PcSelectorRequest(user_id=user_id, status="pending"))
            db.commit()
        return {
            "step": "pc_menu",
            "reason": "pc_online",
            "device_status": pc_status,
            "message": "Choose mode on PC.",
        }

    return {
        "step": "phone_menu",
        "reason": "pc_locked_or_off",
        "device_status": pc_status,
        "message": "Choose mode on iPhone.",
    }


@app.get("/api/stats")
def api_stats(user_id: str, db: Session = Depends(get_db)):
    ensure_user(db, user_id)
    active = get_active_session(db, user_id)

    totals = (
        db.query(
            func.coalesce(func.sum(SessionModel.duration_seconds), 0).label("total_seconds"),
            func.count(SessionModel.id).label("total_sessions"),
        )
        .filter(SessionModel.user_id == user_id, SessionModel.end_time.is_not(None))
        .first()
    )

    streak = db.query(Streak).filter(Streak.user_id == user_id).first()

    return {
        "active_session": to_session_dict(active) if active else None,
        "total_seconds": int(totals.total_seconds or 0),
        "total_sessions": int(totals.total_sessions or 0),
        "streak": {
            "current_streak": streak.current_streak if streak else 0,
            "best_streak": streak.best_streak if streak else 0,
            "last_active_date": str(streak.last_active_date) if streak and streak.last_active_date else None,
        },
    }


@app.get("/api/logs")
def api_logs(
    user_id: str,
    page: int = 1,
    page_size: int = 20,
    mode: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
):
    ensure_user(db, user_id)

    safe_page = max(1, int(page))
    safe_page_size = min(100, max(5, int(page_size)))
    offset = (safe_page - 1) * safe_page_size

    base_query = db.query(SessionModel).filter(
        SessionModel.user_id == user_id,
        SessionModel.end_time.is_not(None),
    )

    if mode in {"study", "coding", "fun"}:
        base_query = base_query.filter(SessionModel.mode == mode)

    try:
        if from_date:
            start_dt = datetime.strptime(from_date, "%Y-%m-%d")
            base_query = base_query.filter(SessionModel.start_time >= start_dt)
        if to_date:
            end_dt = datetime.strptime(to_date, "%Y-%m-%d") + timedelta(days=1)
            base_query = base_query.filter(SessionModel.start_time < end_dt)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    if search:
        s = search.strip().lower()
        if s in {"study", "coding", "fun"}:
            base_query = base_query.filter(SessionModel.mode == s)
        elif s in {"pc_on", "pc_locked", "pc_off"}:
            base_query = base_query.filter(SessionModel.device_status == s)

    total_items = int(base_query.count())
    rows = (
        base_query.order_by(SessionModel.start_time.desc())
        .offset(offset)
        .limit(safe_page_size)
        .all()
    )

    mode_rows = (
        base_query.with_entities(
            SessionModel.mode.label("mode"),
            func.coalesce(func.sum(SessionModel.duration_seconds), 0).label("seconds"),
        )
        .group_by(SessionModel.mode)
        .all()
    )
    mode_totals = {"study": 0, "coding": 0, "fun": 0}
    for row in mode_rows:
        mode_totals[row.mode] = int(row.seconds or 0)

    total_pages = max(1, (total_items + safe_page_size - 1) // safe_page_size)
    active_session = get_active_session(db, user_id)

    return {
        "items": [to_session_dict(row) for row in rows],
        "pagination": {
            "page": safe_page,
            "page_size": safe_page_size,
            "total_items": total_items,
            "total_pages": total_pages,
            "has_prev": safe_page > 1,
            "has_next": safe_page < total_pages,
        },
        "mode_totals_seconds": mode_totals,
        "daily_breakdown": get_last_7_days_breakdown(db, user_id),
        "active_session": to_session_dict(active_session) if active_session else None,
        "applied_filters": {
            "mode": mode,
            "from_date": from_date,
            "to_date": to_date,
            "search": search,
        },
    }


@app.get("/api/weekly", response_model=WeeklyResponse)
def api_weekly(user_id: str, db: Session = Depends(get_db)):
    now = datetime.utcnow()
    week_start = now - timedelta(days=7)

    def mode_total(mode: str) -> int:
        row = (
            db.query(func.coalesce(func.sum(SessionModel.duration_seconds), 0).label("s"))
            .filter(
                SessionModel.user_id == user_id,
                SessionModel.mode == mode,
                SessionModel.end_time.is_not(None),
                SessionModel.start_time >= week_start,
            )
            .first()
        )
        return int(row.s or 0)

    study = mode_total("study")
    coding = mode_total("coding")
    fun = mode_total("fun")

    total_sessions = (
        db.query(func.count(SessionModel.id))
        .filter(
            SessionModel.user_id == user_id,
            SessionModel.end_time.is_not(None),
            SessionModel.start_time >= week_start,
        )
        .scalar()
    )

    last = (
        db.query(SessionModel)
        .filter(SessionModel.user_id == user_id, SessionModel.end_time.is_not(None))
        .order_by(SessionModel.end_time.desc())
        .first()
    )

    return {
        "total_study_seconds": study,
        "total_coding_seconds": coding,
        "total_fun_seconds": fun,
        "total_sessions": int(total_sessions or 0),
        "last_session": to_session_dict(last) if last else None,
        "daily_breakdown": get_last_7_days_breakdown(db, user_id),
    }


@app.get("/api/daily")
def api_daily(user_id: str, db: Session = Depends(get_db)):
    now = datetime.utcnow()
    day_start = now - timedelta(hours=24)

    def mode_total(mode: str) -> int:
        row = (
            db.query(func.coalesce(func.sum(SessionModel.duration_seconds), 0).label("s"))
            .filter(
                SessionModel.user_id == user_id,
                SessionModel.mode == mode,
                SessionModel.end_time.is_not(None),
                SessionModel.start_time >= day_start,
            )
            .first()
        )
        return int(row.s or 0)

    study = mode_total("study")
    coding = mode_total("coding")
    fun = mode_total("fun")

    total_sessions = (
        db.query(func.count(SessionModel.id))
        .filter(
            SessionModel.user_id == user_id,
            SessionModel.end_time.is_not(None),
            SessionModel.start_time >= day_start,
        )
        .scalar()
    )

    last = (
        db.query(SessionModel)
        .filter(SessionModel.user_id == user_id, SessionModel.end_time.is_not(None))
        .order_by(SessionModel.end_time.desc())
        .first()
    )

    return {
        "total_study_seconds": study,
        "total_coding_seconds": coding,
        "total_fun_seconds": fun,
        "total_sessions": int(total_sessions or 0),
        "last_session": to_session_dict(last) if last else None,
        "window": "24h",
    }


@app.post("/api/notify/weekly")
def notify_weekly(user_id: str, db: Session = Depends(get_db)):
    data = api_weekly(user_id, db)
    total_hours = round((data["total_study_seconds"] + data["total_coding_seconds"] + data["total_fun_seconds"]) / 3600, 2)

    send_push_to_user(
        db,
        user_id,
        "Weekly summary",
        f"Sessions: {data['total_sessions']} | Total: {total_hours}h",
        data,
    )
    db.commit()
    return {"ok": True, "summary": data}


@app.post("/api/notify/daily")
def notify_daily(user_id: str, db: Session = Depends(get_db)):
    data = api_daily(user_id, db)
    total_hours = round((data["total_study_seconds"] + data["total_coding_seconds"] + data["total_fun_seconds"]) / 3600, 2)

    send_push_to_user(
        db,
        user_id,
        "24h summary",
        f"Sessions: {data['total_sessions']} | Total: {total_hours}h",
        data,
    )
    db.commit()
    return {"ok": True, "summary": data}


@app.get("/api/widget", response_model=WidgetResponse)
def api_widget(user_id: str, response: Response, db: Session = Depends(get_db)):
    # Prevent CDN/browser caching so widgets fetch fresh state.
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    today = datetime.utcnow().date()
    now = datetime.utcnow()
    today_start = datetime.combine(today, datetime.min.time())
    today_row = (
        db.query(func.coalesce(func.sum(SessionModel.duration_seconds), 0).label("s"))
        .filter(
            SessionModel.user_id == user_id,
            SessionModel.end_time.is_not(None),
            func.date(SessionModel.start_time) == today,
        )
        .first()
    )

    last_5 = (
        db.query(SessionModel)
        .filter(SessionModel.user_id == user_id, SessionModel.end_time.is_not(None))
        .order_by(SessionModel.end_time.desc())
        .limit(5)
        .all()
    )

    streak = db.query(Streak).filter(Streak.user_id == user_id).first()

    study = (
        db.query(func.coalesce(func.sum(SessionModel.duration_seconds), 0).label("s"))
        .filter(SessionModel.user_id == user_id, SessionModel.mode == "study", SessionModel.end_time.is_not(None))
        .scalar()
    )
    coding = (
        db.query(func.coalesce(func.sum(SessionModel.duration_seconds), 0).label("s"))
        .filter(SessionModel.user_id == user_id, SessionModel.mode == "coding", SessionModel.end_time.is_not(None))
        .scalar()
    )
    fun = (
        db.query(func.coalesce(func.sum(SessionModel.duration_seconds), 0).label("s"))
        .filter(SessionModel.user_id == user_id, SessionModel.mode == "fun", SessionModel.end_time.is_not(None))
        .scalar()
    )

    active = get_active_session(db, user_id)
    active_today_seconds = 0
    active_total_seconds = 0
    if active:
        active_start = active.start_time
        if getattr(active_start, "tzinfo", None) is not None:
            active_start = active_start.replace(tzinfo=None)

        active_total_seconds = max(0, int((now - active_start).total_seconds()))
        active_today_seconds = max(0, int((now - max(active_start, today_start)).total_seconds()))

        if active.mode == "study":
            study = int(study or 0) + active_total_seconds
        elif active.mode == "coding":
            coding = int(coding or 0) + active_total_seconds
        elif active.mode == "fun":
            fun = int(fun or 0) + active_total_seconds

    total = max(1, int((study or 0) + (coding or 0) + (fun or 0)))

    return {
        "today_total_seconds": int(today_row.s or 0) + active_today_seconds,
        "current_streak": streak.current_streak if streak else 0,
        "last_5_sessions": [to_session_dict(s) for s in last_5],
        "pie": {
            "study": round((int(study or 0) / total) * 100, 2),
            "coding": round((int(coding or 0) / total) * 100, 2),
            "fun": round((int(fun or 0) / total) * 100, 2),
        },
        "active_session": to_session_dict(active) if active else None,
        "server_time": now,
    }


@app.post("/api/pc/heartbeat")
def pc_heartbeat(payload: PcHeartbeatRequest, db: Session = Depends(get_db)):
    upsert_pc_status(db, payload.device_id, payload.user_id, payload.status)
    db.commit()
    return {"ok": True}


@app.get("/api/pc/next-action")
def pc_next_action(user_id: str, db: Session = Depends(get_db)):
    action = (
        db.query(PcAction)
        .filter(PcAction.user_id == user_id, PcAction.status == "pending")
        .order_by(PcAction.created_at.asc())
        .first()
    )
    if not action:
        return {"action": None}

    return {
        "action": {
            "id": action.id,
            "mode": action.mode,
            "payload": action.payload,
            "created_at": action.created_at,
        }
    }


@app.post("/api/pc/ack")
def pc_ack(payload: PcAckRequest, db: Session = Depends(get_db)):
    action = db.query(PcAction).filter(PcAction.id == payload.action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    action.status = "done"
    action.consumed_at = datetime.utcnow()
    db.commit()
    return {"ok": True}


@app.get("/api/pc/selector-request")
def pc_selector_request(user_id: str, db: Session = Depends(get_db)):
    req = (
        db.query(PcSelectorRequest)
        .filter(PcSelectorRequest.user_id == user_id, PcSelectorRequest.status == "pending")
        .order_by(PcSelectorRequest.created_at.asc())
        .first()
    )
    if not req:
        return {"request": None}

    return {
        "request": {
            "id": req.id,
            "created_at": req.created_at,
        }
    }


@app.post("/api/pc/selector-ack")
def pc_selector_ack(payload: PcSelectorAckRequest, db: Session = Depends(get_db)):
    req = db.query(PcSelectorRequest).filter(PcSelectorRequest.id == payload.request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Selector request not found")

    req.status = "done"
    req.consumed_at = datetime.utcnow()
    db.commit()
    return {"ok": True}
