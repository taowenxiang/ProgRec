ALTER TABLE agent_sessions
ADD COLUMN IF NOT EXISTS owner_token TEXT;

CREATE INDEX IF NOT EXISTS ix_agent_sessions_owner_token
ON agent_sessions(owner_token);
