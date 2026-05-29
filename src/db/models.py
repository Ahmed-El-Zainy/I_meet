from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Date, DateTime,
    Enum, JSON, ForeignKey, func
)
from src.db.session import Base


class Client(Base):
    __tablename__ = "clients"
    client_id  = Column(String(64), primary_key=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)


class Meeting(Base):
    __tablename__ = "meetings"
    meeting_id        = Column(String(64), primary_key=True)
    client_id         = Column(String(64), ForeignKey("clients.client_id"), nullable=False)
    meeting_title_enc = Column(Text, nullable=False)
    participants_enc  = Column(Text, nullable=False)
    transcript_enc    = Column(Text(4294967295))   # LONGTEXT
    summary_enc       = Column(Text(4294967295))
    sentiment_enc     = Column(Text(4294967295))
    meeting_date      = Column(Date)
    duration_seconds  = Column(Integer)
    language_mix      = Column(JSON)
    created_at        = Column(DateTime, default=func.now(), nullable=False)


class ProcessingStatus(Base):
    __tablename__ = "processing_status"
    meeting_id    = Column(String(64), ForeignKey("meetings.meeting_id"), primary_key=True)
    status        = Column(Enum(
        "queued", "transcribing", "summarizing",
        "generating_pdf", "encrypting", "embedding", "complete", "failed"
    ))
    error_message = Column(Text)
    started_at    = Column(DateTime)
    completed_at  = Column(DateTime)


class EncryptedArtifact(Base):
    __tablename__ = "encrypted_artifacts"
    artifact_id   = Column(String(64), primary_key=True)
    meeting_id    = Column(String(64), ForeignKey("meetings.meeting_id"), nullable=False)
    artifact_type = Column(Enum("pdf", "transcript_raw"))
    file_path     = Column(Text, nullable=False)
    file_iv       = Column(String(64), nullable=False)
    created_at    = Column(DateTime, default=func.now(), nullable=False)


class Participant(Base):
    __tablename__ = "participants"
    id            = Column(Integer, primary_key=True, autoincrement=True)
    meeting_id    = Column(String(64), ForeignKey("meetings.meeting_id"), nullable=False)
    speaker_label = Column(String(32), nullable=False)
    name_enc      = Column(Text)
