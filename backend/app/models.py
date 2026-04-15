from sqlalchemy import JSON, BigInteger, Column, Date, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from .database import Base


MODE_ENUM = ("study", "coding", "fun")
DEVICE_STATUS_ENUM = ("pc_on", "pc_locked", "pc_off")
ACTION_STATUS_ENUM = ("pending", "done")


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Session(Base):
    __tablename__ = "sessions"

    id = Column(BigInteger, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    mode = Column(Enum(*MODE_ENUM, name="mode_enum", create_type=False), nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    device_status = Column(
        Enum(*DEVICE_STATUS_ENUM, name="device_status_enum", create_type=False),
        nullable=False,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Streak(Base):
    __tablename__ = "streaks"

    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    current_streak = Column(Integer, nullable=False, default=0)
    best_streak = Column(Integer, nullable=False, default=0)
    last_active_date = Column(Date, nullable=True)


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id = Column(BigInteger, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    endpoint = Column(Text, nullable=False, unique=True)
    p256dh = Column(Text, nullable=False)
    auth = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PcDevice(Base):
    __tablename__ = "pc_devices"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(
        Enum(*DEVICE_STATUS_ENUM, name="device_status_enum", create_type=False),
        nullable=False,
        default="pc_on",
    )
    last_seen = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PcAction(Base):
    __tablename__ = "pc_actions"

    id = Column(BigInteger, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    mode = Column(Enum(*MODE_ENUM, name="mode_enum", create_type=False), nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(
        Enum(*ACTION_STATUS_ENUM, name="action_status_enum", create_type=False),
        nullable=False,
        default="pending",
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    consumed_at = Column(DateTime(timezone=True), nullable=True)


class PcSelectorRequest(Base):
    __tablename__ = "pc_selector_requests"

    id = Column(BigInteger, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(
        Enum(*ACTION_STATUS_ENUM, name="action_status_enum", create_type=False),
        nullable=False,
        default="pending",
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    consumed_at = Column(DateTime(timezone=True), nullable=True)
