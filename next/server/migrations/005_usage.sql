-- Private operational analytics: no names, emails, content, tokens, or URLs.
-- Triggers run in the resource transaction, so rollbacks and request replays
-- cannot count actions which did not happen. No fabricated historical events.
CREATE TABLE IF NOT EXISTS usage_metadata (
    key TEXT PRIMARY KEY, value TEXT NOT NULL
);
INSERT OR IGNORE INTO usage_metadata VALUES ('started_at', strftime('%Y-%m-%dT%H:%M:%SZ','now'));
CREATE TABLE IF NOT EXISTS usage_events (
    event TEXT NOT NULL CHECK(event IN ('channel_created','agent_connected','message_sent','document_created')),
    resource_id TEXT NOT NULL,
    actor_kind TEXT NOT NULL CHECK(actor_kind IN ('human','agent')),
    actor_id TEXT NOT NULL,
    occurred_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    PRIMARY KEY(event, resource_id)
);
CREATE INDEX IF NOT EXISTS usage_event_time ON usage_events(occurred_at);
CREATE TABLE IF NOT EXISTS usage_active_days (
    day TEXT NOT NULL,
    user_id TEXT NOT NULL REFERENCES users(id),
    PRIMARY KEY(day, user_id)
);
CREATE TRIGGER IF NOT EXISTS usage_channel AFTER INSERT ON channels BEGIN
    INSERT INTO usage_events(event,resource_id,actor_kind,actor_id)
        VALUES ('channel_created',NEW.id,'human',NEW.owner_id);
END;
CREATE TRIGGER IF NOT EXISTS usage_agent AFTER INSERT ON participants WHEN NEW.kind='agent' BEGIN
    INSERT INTO usage_events(event,resource_id,actor_kind,actor_id)
        VALUES ('agent_connected',NEW.id,'agent',NEW.id);
END;
CREATE TRIGGER IF NOT EXISTS usage_message AFTER INSERT ON messages BEGIN
    INSERT INTO usage_events(event,resource_id,actor_kind,actor_id)
        SELECT 'message_sent',NEW.id,kind,COALESCE(user_id,id)
        FROM participants WHERE id=NEW.sender_id;
END;
CREATE TRIGGER IF NOT EXISTS usage_document AFTER INSERT ON document_revisions WHEN NEW.revision=1 BEGIN
    INSERT INTO usage_events(event,resource_id,actor_kind,actor_id)
        SELECT 'document_created',NEW.doc_id,kind,COALESCE(user_id,id)
        FROM participants WHERE id=NEW.author_id;
END;
CREATE TRIGGER IF NOT EXISTS usage_human_action AFTER INSERT ON usage_events WHEN NEW.actor_kind='human' BEGIN
    INSERT OR IGNORE INTO usage_active_days VALUES (substr(NEW.occurred_at,1,10),NEW.actor_id);
END;
