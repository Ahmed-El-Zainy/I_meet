from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from src.db.models import Meeting, ProcessingStatus, EncryptedArtifact, Participant, Client


# ── Meetings ──────────────────────────────────────────────────────────────────

def create_meeting(db: Session, meeting_id: str, client_id: str,
                   title_enc: str, participants_enc: str,
                   meeting_date=None) -> Meeting:
    m = Meeting(
        meeting_id=meeting_id,
        client_id=client_id,
        meeting_title_enc=title_enc,
        participants_enc=participants_enc,
        meeting_date=meeting_date,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def get_meeting(db: Session, meeting_id: str) -> Optional[Meeting]:
    return db.query(Meeting).filter(Meeting.meeting_id == meeting_id).first()


def get_meetings_for_client(db: Session, client_id: str) -> list[Meeting]:
    return db.query(Meeting).filter(Meeting.client_id == client_id).all()


def update_meeting_transcript(db: Session, meeting_id: str, transcript_enc: str,
                               duration_seconds: int, language_mix: dict):
    db.query(Meeting).filter(Meeting.meeting_id == meeting_id).update({
        "transcript_enc": transcript_enc,
        "duration_seconds": duration_seconds,
        "language_mix": language_mix,
    })
    db.commit()


def update_meeting_summary(db: Session, meeting_id: str, summary_enc: str):
    db.query(Meeting).filter(Meeting.meeting_id == meeting_id).update({"summary_enc": summary_enc})
    db.commit()


def update_meeting_sentiment(db: Session, meeting_id: str, sentiment_enc: str):
    db.query(Meeting).filter(Meeting.meeting_id == meeting_id).update({"sentiment_enc": sentiment_enc})
    db.commit()


# ── Processing status ─────────────────────────────────────────────────────────

def create_status(db: Session, meeting_id: str) -> ProcessingStatus:
    s = ProcessingStatus(meeting_id=meeting_id, status="queued", started_at=datetime.utcnow())
    db.add(s)
    db.commit()
    return s


def set_status(db: Session, meeting_id: str, status: str, error: str = None):
    update = {"status": status}
    if error:
        update["error_message"] = error
    if status == "complete":
        update["completed_at"] = datetime.utcnow()
    db.query(ProcessingStatus).filter(ProcessingStatus.meeting_id == meeting_id).update(update)
    db.commit()


def get_status(db: Session, meeting_id: str) -> Optional[ProcessingStatus]:
    return db.query(ProcessingStatus).filter(ProcessingStatus.meeting_id == meeting_id).first()


# ── Artifacts ─────────────────────────────────────────────────────────────────

def create_artifact(db: Session, artifact_id: str, meeting_id: str,
                    artifact_type: str, file_path: str, file_iv: str) -> EncryptedArtifact:
    a = EncryptedArtifact(
        artifact_id=artifact_id,
        meeting_id=meeting_id,
        artifact_type=artifact_type,
        file_path=file_path,
        file_iv=file_iv,
    )
    db.add(a)
    db.commit()
    return a


def get_artifact(db: Session, meeting_id: str, artifact_type: str) -> Optional[EncryptedArtifact]:
    return db.query(EncryptedArtifact).filter(
        EncryptedArtifact.meeting_id == meeting_id,
        EncryptedArtifact.artifact_type == artifact_type,
    ).first()


# ── Participants ──────────────────────────────────────────────────────────────

def upsert_participant(db: Session, meeting_id: str, speaker_label: str, name_enc: str = None):
    existing = db.query(Participant).filter(
        Participant.meeting_id == meeting_id,
        Participant.speaker_label == speaker_label,
    ).first()
    if not existing:
        db.add(Participant(meeting_id=meeting_id, speaker_label=speaker_label, name_enc=name_enc))
        db.commit()


# ── Clients ───────────────────────────────────────────────────────────────────

def get_client(db: Session, client_id: str) -> Optional[Client]:
    return db.query(Client).filter(Client.client_id == client_id).first()
