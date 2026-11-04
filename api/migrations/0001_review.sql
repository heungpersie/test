-- Review artifact only. Apply changes with Alembic, not this file.
BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 0001

CREATE TABLE users (
    id UUID NOT NULL, 
    email VARCHAR(320) NOT NULL, 
    password_hash TEXT NOT NULL, 
    role VARCHAR(20) DEFAULT 'presenter' NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_users PRIMARY KEY (id), 
    CONSTRAINT ck_users_role_allowed CHECK (role IN ('presenter', 'expert')), 
    CONSTRAINT ck_users_email_normalized CHECK (email = lower(trim(email)) AND length(email) > 0), 
    CONSTRAINT uq_users_email UNIQUE (email)
);

CREATE TABLE presentations (
    id UUID NOT NULL, 
    owner_id UUID NOT NULL, 
    title VARCHAR(200) NOT NULL, 
    description TEXT, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_presentations PRIMARY KEY (id), 
    CONSTRAINT ck_presentations_title_not_blank CHECK (length(trim(title)) > 0), 
    CONSTRAINT fk_presentations_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE INDEX ix_presentations_owner_id ON presentations (owner_id);

CREATE TABLE rehearsals (
    id UUID NOT NULL, 
    presentation_id UUID NOT NULL, 
    sequence INTEGER NOT NULL, 
    mode VARCHAR(10) NOT NULL, 
    status VARCHAR(20) DEFAULT 'created' NOT NULL, 
    video_key TEXT, 
    video_content_type VARCHAR(100), 
    duration_seconds DOUBLE PRECISION, 
    consented_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_rehearsals PRIMARY KEY (id), 
    CONSTRAINT ck_rehearsals_mode_allowed CHECK (mode IN ('upload', 'live')), 
    CONSTRAINT ck_rehearsals_status_allowed CHECK (status IN ('created', 'live', 'uploaded', 'queued', 'analyzing', 'done', 'failed')), 
    CONSTRAINT ck_rehearsals_duration_positive CHECK (duration_seconds > 0), 
    CONSTRAINT ck_rehearsals_sequence_positive CHECK (sequence >= 1), 
    CONSTRAINT fk_rehearsals_presentation_id_presentations FOREIGN KEY(presentation_id) REFERENCES presentations (id) ON DELETE RESTRICT, 
    CONSTRAINT uq_rehearsals_presentation_id UNIQUE (presentation_id, sequence)
);

CREATE INDEX ix_rehearsals_expires_at ON rehearsals (expires_at);

CREATE TABLE analysis_jobs (
    id UUID NOT NULL, 
    rehearsal_id UUID NOT NULL, 
    external_job_id TEXT, 
    status VARCHAR(20) DEFAULT 'queued' NOT NULL, 
    stage VARCHAR(50), 
    progress INTEGER DEFAULT '0' NOT NULL, 
    attempt INTEGER DEFAULT '1' NOT NULL, 
    error_code VARCHAR(100), 
    error_message TEXT, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    started_at TIMESTAMP WITH TIME ZONE, 
    finished_at TIMESTAMP WITH TIME ZONE, 
    CONSTRAINT pk_analysis_jobs PRIMARY KEY (id), 
    CONSTRAINT ck_analysis_jobs_status_allowed CHECK (status IN ('queued', 'running', 'succeeded', 'failed')), 
    CONSTRAINT ck_analysis_jobs_attempt_positive CHECK (attempt >= 1), 
    CONSTRAINT ck_analysis_jobs_progress_range CHECK (progress BETWEEN 0 AND 100), 
    CONSTRAINT fk_analysis_jobs_rehearsal_id_rehearsals FOREIGN KEY(rehearsal_id) REFERENCES rehearsals (id) ON DELETE RESTRICT, 
    CONSTRAINT uq_analysis_jobs_external_job_id UNIQUE (external_job_id)
);

CREATE INDEX ix_analysis_jobs_rehearsal_id ON analysis_jobs (rehearsal_id);

CREATE TABLE live_sessions (
    id UUID NOT NULL, 
    rehearsal_id UUID NOT NULL, 
    status VARCHAR(20) DEFAULT 'prepared' NOT NULL, 
    token_hash TEXT, 
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    started_at TIMESTAMP WITH TIME ZONE, 
    ended_at TIMESTAMP WITH TIME ZONE, 
    CONSTRAINT pk_live_sessions PRIMARY KEY (id), 
    CONSTRAINT ck_live_sessions_status_allowed CHECK (status IN ('prepared', 'active', 'ended', 'expired')), 
    CONSTRAINT fk_live_sessions_rehearsal_id_rehearsals FOREIGN KEY(rehearsal_id) REFERENCES rehearsals (id) ON DELETE RESTRICT, 
    CONSTRAINT uq_live_sessions_rehearsal_id UNIQUE (rehearsal_id)
);

INSERT INTO alembic_version (version_num) VALUES ('0001') RETURNING alembic_version.version_num;

COMMIT;

