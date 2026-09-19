import { useEffect, useRef, useState } from "react";
import { DocsPanel } from "./DocsPanel";
import { MentionEditor, mentionBody, type InlineMention, type MentionEditorHandle } from "./MentionEditor";
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
  documentsChanged,
  documentsOpening,
  disabled = false,
}: {
  channelId: string;
  userId: string;
  rootId?: string | null;
  participants: Participant[];
  documents: DocMeta[];
  sent: (m: Message) => void;
  documentsChanged: () => void;
  documentsOpening: () => void;
  disabled?: boolean;
}) {
  const storageKey = `codifica:message:${userId}:${channelId}:${rootId || "general"}`;
  const [recovered] = useState(() => {
    try {
      return JSON.parse(sessionStorage.getItem(storageKey) || "null") as {
        body: string;
        mentions: string[];
        inlineMentions?: InlineMention[];
        docRefs: DocRef[];
        pending: { key: string; requestId: string } | null;
      } | null;
    } catch {
      return null;
    }
  });
  const [body, setBody] = useState(recovered?.body || ""),
    [mentions, setMentions] = useState<string[]>(recovered?.mentions || []),
    [inlineMentions, setInlineMentions] = useState<InlineMention[]>(recovered?.inlineMentions || []),
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
  const [choosingDoc, setChoosingDoc] = useState(false);
  const docDialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    if (choosingDoc) docDialog.current?.showModal();
  }, [choosingDoc]);
  const editor = useRef<MentionEditorHandle>(null);
  function persist() {
    try {
      sessionStorage.setItem(
        storageKey,
        JSON.stringify({ body, mentions, inlineMentions, docRefs, pending: pending.current }),
      );
    } catch {
      setError(
        "Draft could not be saved locally. Keep this conversation open.",
      );
    }
  }
  useEffect(() => {
    if (body || mentions.length || docRefs.length || pending.current) persist();
    else sessionStorage.removeItem(storageKey);
  }, [body, mentions, inlineMentions, docRefs]);
  async function send() {
    if ((!body.trim() && !docRefs.length) || busy || disabled) return;
    setBusy(true);
    setError("");
    const payload = {
      body: mentionBody(body, inlineMentions).trim(),
      rootMessageId: rootId,
      mentions: [...new Set([...mentions, ...inlineMentions.flatMap((m) => m.ids)])],
      docRefs: docRefs.map(({ docId, revision, title, startLine, endLine }) => ({ docId, revision, title, startLine, endLine })),
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
      setInlineMentions([]);
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
    <>
    <form
      className="composer"
      onSubmit={(e) => {
        e.preventDefault();
        void send();
      }}
    >
      <MentionEditor ref={editor}
        label={rootId ? "Reply" : "Message"}
        placeholder={
          disabled
            ? "This channel is archived"
            : rootId
              ? "Continue the conversation…"
              : "Write a message. Mention an agent to bring it in."
        }
        body={body} mentions={inlineMentions} participants={participants}
        disabled={disabled || busy || (!!error && !!pending.current)}
        change={(text, spans) => { setBody(text); setInlineMentions(spans); }}
        send={() => void send()}
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
          <button type="button" className="ask-agents"
            disabled={disabled || busy || !!pending.current || !participants.some((p) => p.kind === "agent")}
            title="Select all current agents. Only active sessions can respond."
            onClick={() => editor.current?.all()}>
            Ask all agents
          </button>
          <button type="button"
            aria-label="Mention participant"
            disabled={disabled || busy || !!pending.current}
            onClick={() => editor.current?.open()}
          >
            @ Mention
          </button>
          <button type="button"
            aria-label="Attach document"
            disabled={disabled || busy || !!pending.current}
            onClick={() => { documentsOpening(); setChoosingDoc(true); }}
          >
            ＋ Document
          </button>
        </div>
        <button className="primary" disabled={disabled || busy || (!body.trim() && !docRefs.length)}>
          {busy ? "Sending…" : error ? "Retry send" : rootId ? "Reply" : "Send"}
        </button>
      </div>
      {error && (
        <p className="notice" role="alert">
          {error} Your message is preserved.
        </p>
      )}
    </form>
    {choosingDoc && (
      <dialog ref={docDialog} aria-label="Documents" className="document-dialog"
        onCancel={(e) => { e.preventDefault(); docDialog.current?.querySelector<HTMLButtonElement>('[aria-label="Close docs"]')?.click(); }}>
        <DocsPanel userId={userId} channelId={channelId} documents={documents}
          archived={disabled} close={() => setChoosingDoc(false)} changed={documentsChanged}
          attach={(doc) => {
            setDocRefs((v) => [...v.filter((x) => x.docId !== doc.id), {
              docId: doc.id, revision: doc.revision, title: doc.title, kind: doc.kind,
              filename: doc.filename, mediaType: doc.mediaType, size: doc.size,
            }]);
            setChoosingDoc(false);
          }} />
      </dialog>
    )}
    </>
  );
}
