from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


ModeLiteral = Literal["study", "coding", "fun"]
StatusLiteral = Literal["pc_on", "pc_locked", "pc_off"]


class TapRequest(BaseModel):
    user_id: str = Field(min_length=1)
    mode: Optional[ModeLiteral] = None
    device_status: StatusLiteral = "pc_on"


class StartRequest(BaseModel):
    user_id: str = Field(min_length=1)
    mode: ModeLiteral
    device_status: StatusLiteral = "pc_on"


class StopRequest(BaseModel):
    user_id: str = Field(min_length=1)
    device_status: StatusLiteral = "pc_on"


class SubscribeRequest(BaseModel):
    user_id: str = Field(min_length=1)
    endpoint: str = Field(min_length=1)
    keys: dict


class PcHeartbeatRequest(BaseModel):
    device_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    status: StatusLiteral


class PcAckRequest(BaseModel):
    action_id: int


class PcSelectorAckRequest(BaseModel):
    request_id: int


class SessionOut(BaseModel):
    id: int
    mode: ModeLiteral
    start_time: datetime
    end_time: Optional[datetime]
    duration_seconds: Optional[int]
    device_status: StatusLiteral


class StartStopResponse(BaseModel):
    action: Literal["started", "stopped"]
    session: SessionOut
    message: Optional[str] = None


class WeeklyResponse(BaseModel):
    total_study_seconds: int
    total_coding_seconds: int
    total_fun_seconds: int
    total_sessions: int
    last_session: Optional[SessionOut]
    daily_breakdown: list


class WidgetResponse(BaseModel):
    today_total_seconds: int
    current_streak: int
    last_5_sessions: list[SessionOut]
    pie: dict
