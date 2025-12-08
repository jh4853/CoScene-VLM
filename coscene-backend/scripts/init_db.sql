-- CoScene Database Schema - MVP
-- PostgreSQL 16 with basic tables for session management, scene versioning, and rendering

-- Create database (run separately)
-- CREATE DATABASE coscene;

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Sessions table: User editing sessions
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    started_at TIMESTAMP DEFAULT NOW(),
    last_active_at TIMESTAMP DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'completed')),
    extra_metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_status ON sessions(status);

-- Messages table: Conversation history
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW(),
    extra_metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_messages_session ON messages(session_id, timestamp);

-- Scene versions table: USD snapshots with full content
CREATE TABLE IF NOT EXISTS scene_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    version_number INT NOT NULL,
    parent_version_id UUID REFERENCES scene_versions(id) ON DELETE SET NULL,
    usd_content TEXT NOT NULL,
    created_by_message_id UUID REFERENCES messages(id) ON DELETE SET NULL,
    checksum VARCHAR(64),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(session_id, version_number)
);

CREATE INDEX idx_scene_versions_session ON scene_versions(session_id, version_number DESC);
CREATE INDEX idx_scene_versions_checksum ON scene_versions(checksum);

-- Renders table: Store rendered images as BYTEA
CREATE TABLE IF NOT EXISTS renders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scene_version_id UUID NOT NULL REFERENCES scene_versions(id) ON DELETE CASCADE,
    camera_angle VARCHAR(50) NOT NULL,
    quality VARCHAR(20) NOT NULL CHECK (quality IN ('preview', 'verification', 'final')),
    width INT NOT NULL,
    height INT NOT NULL,
    blob_data BYTEA NOT NULL,
    render_time_ms INT,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP
);

CREATE INDEX idx_renders_scene ON renders(scene_version_id, camera_angle);
CREATE INDEX idx_renders_expires ON renders(expires_at) WHERE expires_at IS NOT NULL;

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for sessions table
CREATE TRIGGER update_sessions_updated_at BEFORE UPDATE ON sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to cleanup expired renders
CREATE OR REPLACE FUNCTION cleanup_expired_renders()
RETURNS void AS $$
BEGIN
    DELETE FROM renders
    WHERE expires_at IS NOT NULL AND expires_at < NOW();
END;
$$ LANGUAGE plpgsql;

-- Comments for documentation
COMMENT ON TABLE sessions IS 'User editing sessions with status tracking';
COMMENT ON TABLE messages IS 'Conversation history between user and assistant';
COMMENT ON TABLE scene_versions IS 'Full USD scene snapshots with version tracking';
COMMENT ON TABLE renders IS 'Rendered images stored as BYTEA for MVP';

COMMENT ON COLUMN renders.blob_data IS 'PNG image data stored as BYTEA';
COMMENT ON COLUMN renders.expires_at IS 'Optional expiration for preview renders';
COMMENT ON COLUMN scene_versions.checksum IS 'SHA-256 hash of usd_content for deduplication';
