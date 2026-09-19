import { useEffect, useRef, useState } from "react";
import {
  api,
  post,
  patch,
  uid,
  errorText,
  ApiError,
  type Doc,
  type DocMeta,
  type DocRef,
} from "./api";
import { Markdown, Notice } from "./ui";
type Pending = { key: string; requestId: string };
type Draft = {
  doc: Doc | null;
  title: string;
  body: string;
  pending: Pending | null;
};
function stored(key: string): Draft | null {
  try {
    return JSON.parse(sessionStorage.getItem(key) || "null");
  } catch {
    return null;
  }
}
export function DocsPanel({
  userId,
  channelId,
  documents,
  initialRef,
  close,
  changed,
  archived,
}: {
  userId: string;
  channelId: string;
  documents: DocMeta[];
  initialRef?: DocRef;
  close: () => void;
  changed: () => void;
  archived: boolean;
}) {
  const storageKey = `codifica:draft:${userId}:${channelId}`;
  const [recovered] = useState(() => stored(storageKey));
  const [doc, setDoc] = useState<Doc | null>(recovered?.doc || null),
    [title, setTitle] = useState(recovered?.title || ""),
    [body, setBody] = useState(recovered?.body || "");
  const [editing, setEditing] = useState(!!recovered),
    [preview, setPreview] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(
      recovered ? "Recovered your unsaved draft." : "",
    ),
    [conflict, setConflict] = useState<Doc | null>(null),
    [dirty, setDirty] = useState(!!recovered);
  const pending = useRef<Pending | null>(recovered?.pending || null);
  function persist() {
    try {
      sessionStorage.setItem(
        storageKey,
        JSON.stringify({ doc, title, body, pending: pending.current }),
      );
    } catch {
      setError(
        "This browser could not save the draft locally. Keep this panel open until you save.",
      );
    }
  }
  useEffect(() => {
    if (dirty) persist();
    else sessionStorage.removeItem(storageKey);
  }, [doc, title, body, dirty]);
  useEffect(() => {
    const protect = (e: BeforeUnloadEvent) => {
      if (dirty) {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", protect);
    return () => window.removeEventListener("beforeunload", protect);
  }, [dirty]);
  function mayDiscard() {
    if (pending.current) {
      setError("Retry the pending save before opening another document.");
      return false;
    }
    return !dirty || window.confirm("Discard your unsaved document changes?");
  }
  async function load(id: string, revision?: number) {
    if (!mayDiscard()) return;
    setError("");
    try {
      const d = await api<Doc>(
        `/channels/${channelId}/docs/${id}${revision ? `?revision=${revision}` : ""}`,
      );
      setDoc(d);
      setTitle(d.title);
      setBody(d.body);
      setEditing(false);
      setDirty(false);
      setConflict(null);
    } catch (e) {
      setError(errorText(e));
    }
  }
  useEffect(() => {
    if (initialRef && !recovered)
      void load(initialRef.docId, initialRef.revision);
  }, [initialRef?.docId, initialRef?.revision]);
  async function save() {
    setBusy(true);
    setError("");
    const key = JSON.stringify({
      id: doc?.id,
      revision: doc?.revision,
      title,
      body,
    });
    if (pending.current && pending.current.key !== key) {
      setError(
        "Retry your original draft first; its previous save has an uncertain result.",
      );
      setBusy(false);
      return;
    }
    if (!pending.current) pending.current = { key, requestId: uid() };
    persist();
    try {
      const payload = { title, body, requestId: pending.current.requestId };
      const d = doc
        ? await patch<Doc>(`/channels/${channelId}/docs/${doc.id}`, {
            ...payload,
            expectedRevision: doc.revision,
          })
        : await post<Doc>(`/channels/${channelId}/docs`, payload);
      pending.current = null;
      sessionStorage.removeItem(storageKey);
      setDoc(d);
      setDirty(false);
      setEditing(false);
      setConflict(null);
      changed();
    } catch (e) {
      if (
        e instanceof ApiError &&
        [400, 401, 403, 404, 409, 413, 422].includes(e.status)
      )
        pending.current = null;
      persist();
      if (e instanceof ApiError && e.status === 409 && doc) {
        setError(
          "This document has changed. Your draft is preserved. Review the latest version before saving again.",
        );
        try {
          setConflict(await api<Doc>(`/channels/${channelId}/docs/${doc.id}`));
        } catch {}
      } else setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  function newDoc() {
    if (!mayDiscard()) return;
    setDoc(null);
    setTitle("");
    setBody("");
    setEditing(true);
    setDirty(false);
    setError("");
    setConflict(null);
  }
  function exportDoc() {
    const url = URL.createObjectURL(
      new Blob([doc?.body || ""], { type: "text/markdown" }),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = `${(doc?.title || "document").replace(/[^a-z0-9_-]/gi, "-")}-v${doc?.revision}.md`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  const latest =
    documents.find((d) => d.id === doc?.id)?.revision || doc?.revision || 1;
  return (
    <section className="docs-panel">
      <header className="panel-header">
        <div>
          <h2>Docs</h2>
          <p>Shared context for everyone here.</p>
        </div>
        <button className="icon-button" aria-label="Close docs" onClick={close}>
          ×
        </button>
      </header>
      <div className="doc-nav">
        <select
          aria-label="Choose document"
          value={doc?.id || ""}
          onChange={(e) => {
            if (e.target.value) void load(e.target.value);
          }}
        >
          <option value="">Choose a document</option>
          {documents.map((d) => (
            <option key={d.id} value={d.id}>
              {d.title}
            </option>
          ))}
        </select>
        <button onClick={newDoc} disabled={archived}>
          New doc
        </button>
      </div>
      {!doc && !editing && (
        <div className="empty-state small">
          <span className="empty-symbol">▤</span>
          <h3>A common reference point.</h3>
          <p>
            Keep specifications, decisions, and notes alongside the
            conversation.
          </p>
          <button className="primary" onClick={newDoc} disabled={archived}>
            Create a document
          </button>
        </div>
      )}
      {(doc || editing) && (
        <div className="doc-content">
          {editing ? (
            <>
              <label>
                Title
                <input
                  aria-label="Document title"
                  value={title}
                  disabled={busy || !!pending.current}
                  onChange={(e) => {
                    setTitle(e.target.value);
                    setDirty(true);
                  }}
                />
              </label>
              <div className="doc-toolbar">
                <span>Markdown · draft saved in this tab</span>
                <button onClick={() => setPreview((v) => !v)}>
                  {preview ? "Edit" : "Preview"}
                </button>
              </div>
              {preview ? (
                <Markdown>{body}</Markdown>
              ) : (
                <textarea
                  className="doc-editor"
                  aria-label="Document content"
                  value={body}
                  disabled={busy || !!pending.current}
                  onChange={(e) => {
                    setBody(e.target.value);
                    setDirty(true);
                  }}
                />
              )}
            </>
          ) : (
            <>
              <h2>{doc?.title}</h2>
              <div className="doc-toolbar">
                <span>Viewing revision {doc?.revision}</span>
                <select
                  aria-label="Document revision"
                  value={doc?.revision}
                  onChange={(e) => {
                    if (doc) void load(doc.id, Number(e.target.value));
                  }}
                >
                  {Array.from({ length: latest }, (_, i) => (
                    <option key={i + 1} value={i + 1}>
                      Revision {i + 1}
                    </option>
                  ))}
                </select>
                <button
                  onClick={() => {
                    if (doc) void load(doc.id);
                  }}
                >
                  View latest
                </button>
                <button onClick={exportDoc}>Export</button>
                <button disabled={archived} onClick={() => setEditing(true)}>
                  Edit
                </button>
              </div>
              <Markdown>{doc?.body || ""}</Markdown>
            </>
          )}
          {error && <Notice>{error}</Notice>}
          {conflict && (
            <section className="conflict">
              <h3>Latest: revision {conflict.revision}</h3>
              <Markdown>{conflict.body}</Markdown>
              <button
                onClick={() => {
                  setDoc(conflict);
                  setConflict(null);
                  setError(
                    "Latest revision selected. Reconcile your draft above, then save.",
                  );
                }}
              >
                Use this revision as the new base
              </button>
            </section>
          )}
          {editing && (
            <button
              className="primary"
              disabled={busy || !!conflict || !title.trim() || archived}
              onClick={() => void save()}
            >
              {busy ? "Saving…" : "Save document"}
            </button>
          )}
        </div>
      )}
    </section>
  );
}
