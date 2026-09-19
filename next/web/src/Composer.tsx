import { useEffect, useRef, useState } from "react";
import {
  type DocMeta,
  type DocRef,
  type Participant,
  type Message,
  post,
  uid,
  errorText,
  ApiError,
} from "./api";
export function Composer({
  channelId,
  userId,
  rootId = null,
  participants,
  documents,
  sent,
  disabled = false,
}: {
  channelId: string;
  userId: string;
  rootId?: string | null;
  participants: Participant[];
  documents: DocMeta[];
  sent: (m: Message) => void;
  disabled?: boolean;
}) {
  const storageKey = `codifica:message:${userId}:${channelId}:${rootId || "general"}`;
  const [recovered] = useState(() => {
    try {
      return JSON.parse(sessionStorage.getItem(storageKey) || "null") as {
        body: string;
        mentions: string[];
        docRefs: DocRef[];
        pending: { key: string; requestId: string } | null;
      } | null;
    } catch {
      return null;
    }
  });
  const [body, setBody] = useState(recovered?.body || ""),
    [mentions, setMentions] = useState<string[]>(recovered?.mentions || []),
    [docRefs, setDocRefs] = useState<DocRef[]>(recovered?.docRefs || []),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(
      recovered?.pending
        ? "Previous send result is uncertain. Retry to recover it."
        : "",
    );
  const pending = useRef<{ key: string; requestId: string } | null>(
    recovered?.pending || null,
  );
  function persist() {
    try {
      sessionStorage.setItem(
        storageKey,
        JSON.stringify({ body, mentions, docRefs, pending: pending.current }),
      );
    } catch {
      setError(
        "Draft could not be saved locally. Keep this conversation open.",
      );
    }
  }
  useEffect(() => {
    if (body || pending.current) persist();
    else sessionStorage.removeItem(storageKey);
  }, [body, mentions, docRefs]);
  async function send() {
    if (!body.trim() || busy) return;
    setBusy(true);
    setError("");
    const payload = {
      body: body.trim(),
      rootMessageId: rootId,
      mentions,
      docRefs,
    };
    const key = JSON.stringify(payload);
    if (pending.current && pending.current.key !== key) {
      setError("Retry the previous message before changing it.");
      setBusy(false);
      return;
    }
    if (!pending.current) pending.current = { key, requestId: uid() };
    persist();
    try {
      const m = await post<Message>(`/channels/${channelId}/messages`, {
        ...payload,
        requestId: pending.current.requestId,
      });
      pending.current = null;
      sessionStorage.removeItem(storageKey);
      setBody("");
      setMentions([]);
      setDocRefs([]);
      sent(m);
    } catch (e) {
      if (
        e instanceof ApiError &&
        [400, 401, 403, 404, 409, 413, 422].includes(e.status)
      )
        pending.current = null;
      persist();
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <form
      className="composer"
      onSubmit={(e) => {
        e.preventDefault();
        void send();
      }}
    >
      <textarea
        aria-label={rootId ? "Reply" : "Message"}
        placeholder={
          disabled
            ? "This channel is archived"
            : rootId
              ? "Continue the conversation…"
              : "Write a message. Mention an agent to bring it in."
        }
        value={body}
        disabled={disabled || busy || (!!error && !!pending.current)}
        onChange={(e) => setBody(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
            e.preventDefault();
            void send();
          }
        }}
      />
      {(mentions.length > 0 || docRefs.length > 0) && (
        <div className="chips">
          {mentions.map((id) => (
            <button
              type="button"
              key={id}
              disabled={busy || !!pending.current}
              onClick={() => setMentions((v) => v.filter((x) => x !== id))}
            >
              @{participants.find((p) => p.id === id)?.name} ×
            </button>
          ))}
          {docRefs.map((d) => (
            <button
              type="button"
              key={d.docId}
              disabled={busy || !!pending.current}
              onClick={() =>
                setDocRefs((v) => v.filter((x) => x.docId !== d.docId))
              }
            >
              {d.title} · v{d.revision} ×
            </button>
          ))}
        </div>
      )}
      <div className="composer-tools">
        <div className="composer-selects">
          <select
            aria-label="Mention participant"
            disabled={disabled || busy || !!pending.current}
            value=""
            onChange={(e) => {
              if (e.target.value)
                setMentions((v) => [...new Set([...v, e.target.value])]);
            }}
          >
            <option value="">@ Mention</option>
            {participants.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
          <select
            aria-label="Attach document"
            disabled={disabled || busy || !!pending.current}
            value=""
            onChange={(e) => {
              const d = documents.find((x) => x.id === e.target.value);
              if (d)
                setDocRefs((v) => [
                  ...v.filter((x) => x.docId !== d.id),
                  { docId: d.id, revision: d.revision, title: d.title },
                ]);
            }}
          >
            <option value="">＋ Document</option>
            {documents.map((d) => (
              <option key={d.id} value={d.id}>
                {d.title} · v{d.revision}
              </option>
            ))}
          </select>
        </div>
        <button className="primary" disabled={disabled || busy || !body.trim()}>
          {busy ? "Sending…" : error ? "Retry send" : rootId ? "Reply" : "Send"}
        </button>
      </div>
      {error && (
        <p className="notice" role="alert">
          {error} Your message is preserved.
        </p>
      )}
    </form>
  );
}
