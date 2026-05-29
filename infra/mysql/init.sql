CREATE DATABASE IF NOT EXISTS meeting_intelligence;
USE meeting_intelligence;

CREATE TABLE IF NOT EXISTS clients (
    client_id  VARCHAR(64) PRIMARY KEY,
    created_at DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS meetings (
    meeting_id        VARCHAR(64)  PRIMARY KEY,
    client_id         VARCHAR(64)  NOT NULL,
    meeting_title_enc TEXT         NOT NULL,
    participants_enc  TEXT         NOT NULL,
    transcript_enc    LONGTEXT,
    summary_enc       LONGTEXT,
    sentiment_enc     LONGTEXT,
    meeting_date      DATE,
    duration_seconds  INT,
    language_mix      JSON,
    created_at        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES clients(client_id)
);

CREATE TABLE IF NOT EXISTS processing_status (
    meeting_id    VARCHAR(64) PRIMARY KEY,
    status        ENUM('queued','transcribing','summarizing',
                       'generating_pdf','encrypting','embedding','complete','failed'),
    error_message TEXT,
    started_at    DATETIME,
    completed_at  DATETIME,
    FOREIGN KEY (meeting_id) REFERENCES meetings(meeting_id)
);

CREATE TABLE IF NOT EXISTS encrypted_artifacts (
    artifact_id   VARCHAR(64) PRIMARY KEY,
    meeting_id    VARCHAR(64) NOT NULL,
    artifact_type ENUM('pdf','transcript_raw'),
    file_path     TEXT        NOT NULL,
    file_iv       VARCHAR(64) NOT NULL,
    created_at    DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (meeting_id) REFERENCES meetings(meeting_id)
);

CREATE TABLE IF NOT EXISTS participants (
    id            INT         AUTO_INCREMENT PRIMARY KEY,
    meeting_id    VARCHAR(64) NOT NULL,
    speaker_label VARCHAR(32) NOT NULL,
    name_enc      TEXT,
    FOREIGN KEY (meeting_id) REFERENCES meetings(meeting_id)
);

-- Pre-seed sample clients
INSERT IGNORE INTO clients (client_id) VALUES ('client_a'), ('client_b');
