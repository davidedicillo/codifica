CREATE TABLE IF NOT EXISTS document_images (
    doc_id TEXT PRIMARY KEY REFERENCES documents(id),
    filename TEXT NOT NULL,
    media_type TEXT NOT NULL,
    size INTEGER NOT NULL,
    content BLOB NOT NULL
);
