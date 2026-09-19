import { useEffect, useRef, useState } from "react";
import {
  api,
  errorText,
  type User,
  type Channel,
  type Message,
  type Participant,
  type DocMeta,
  type DocRef,
  ApiError,
  imageUrl,
} from "./api";
import { Avatar, Markdown, Time, Notice } from "./ui";
import { Composer } from "./Composer";
import { DocsPanel } from "./DocsPanel";
import { InviteDialog, ManageDialog, RenameAgentDialog } from "./ChannelSettings";
export function ChannelPage({
  channel,
  user,
  refreshChannels,
}: {
  channel: Channel;
  user: User;
  refreshChannels: () => void;
}) {
  const [messages, setMessages] = useState<Message[]>([]),
    [participants, setParticipants] = useState<Participant[]>([]),
    [docs, setDocs] = useState<DocMeta[]>([]),
    [thread, setThread] = useState<Message | null>(null),
    [replies, setReplies] = useState<Message[]>([]),
    [panel, setPanel] = useState<"people" | "docs" | null>(null),
    [docRef, setDocRef] = useState<DocRef | undefined>(),
    [invite, setInvite] = useState<"human" | "agent" | null>(null),
    [manage, setManage] = useState(false),
    [renaming, setRenaming] = useState<Participant | null>(null),
    [error, setError] = useState(""),
    [connected, setConnected] = useState(true),
    [loading, setLoading] = useState(true);
  const end = useRef<HTMLDivElement>(null);
  const threadId = useRef<string | null>(null);
  function merge(items: Message[], incoming: Message[]) {
    const map = new Map(items.map((m) => [m.id, m]));
    for (const m of incoming) map.set(m.id, m);
    return [...map.values()].sort((a, b) => a.sequence - b.sequence);
  }
  async function refreshPeople() {
    setParticipants(
      (
        await api<{ participants: Participant[] }>(
          `/channels/${channel.id}/participants`,
        )
      ).participants,
    );
  }
  async function refreshDocs() {
    setDocs(
      (await api<{ documents: DocMeta[] }>(`/channels/${channel.id}/docs`))
        .documents,
    );
  }
  async function refresh() {
    try {
      const history: Message[] = [];
      let after = 0;
      while (true) {
        const r = await api<{ messages: Message[]; nextSequence: number }>(
          `/channels/${channel.id}/messages?limit=100&afterSequence=${after}`,
        );
        history.push(...r.messages);
        if (r.messages.length < 100 || r.nextSequence <= after) break;
        after = r.nextSequence;
      }
      setMessages(history);
      await Promise.all([refreshPeople(), refreshDocs()]);
      setError("");
      return true;
    } catch (e) {
      setError(errorText(e));
      return false;
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    void refresh();
  }, [channel.id]);
  useEffect(() => {
    let alive = true;
    const controller = new AbortController();
    let cursor = 0;
    async function listen() {
      while (alive) {
        try {
          const r = await api<{
            events: { sequence: number; kind: string; data: unknown }[];
            nextSequence: number;
          }>(`/channels/${channel.id}/events?afterSequence=${cursor}&wait=25`, {
            signal: controller.signal,
          });
          if (!alive) return;
          if (r.events.length) {
            if (!(await refresh()))
              throw new Error("Could not refresh channel");
            const id = threadId.current;
            if (id) await loadReplies(id);
            refreshChannels();
          }
          cursor = r.nextSequence;
          setConnected(true);
        } catch (e) {
          if (!alive) return;
          setConnected(false);
          if (e instanceof ApiError && (e.status === 401 || e.status === 403)) {
            setError("Channel access ended. Refresh or sign in again.");
            return;
          }
          await new Promise((r) => setTimeout(r, 2000));
        }
      }
    }
    void listen();
    const timer = setInterval(() => {
      void refreshPeople().catch(() => {});
    }, 15000);
    return () => {
      alive = false;
      controller.abort();
      clearInterval(timer);
    };
  }, [channel.id]);
  useEffect(() => {
    end.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length]);
  async function loadReplies(id: string) {
    const result: Message[] = [];
    let cursor = 0;
    while (true) {
      const r = await api<{ messages: Message[]; nextSequence: number }>(
        `/channels/${channel.id}/messages?rootMessageId=${id}&afterSequence=${cursor}&limit=100`,
      );
      result.push(...r.messages);
      if (r.messages.length < 100 || r.nextSequence <= cursor) break;
      cursor = r.nextSequence;
    }
    if (threadId.current === id) setReplies(result);
  }
  function openThread(m: Message) {
    setPanel(null);
    setThread(m);
    threadId.current = m.id;
    setReplies([]);
    void loadReplies(m.id).catch((e) => setError(errorText(e)));
  }
  function openDoc(ref: DocRef) {
    setThread(null);
    threadId.current = null;
    setDocRef(ref);
    setPanel("docs");
  }
  const self = participants.find(
    (p) => p.userId === user.id && p.kind === "human",
  );
  async function remove(p: Participant) {
    if (
      !window.confirm(
        p.id === self?.id
          ? "Leave this channel?"
          : `Remove ${p.name} from this channel?`,
      )
    )
      return;
    try {
      await api(`/channels/${channel.id}/participants/${p.id}`, {
        method: "DELETE",
      });
      await refreshPeople();
      refreshChannels();
    } catch (e) {
      setError(errorText(e));
    }
  }
  function messageView(m: Message, isRoot = true) {
    const p = participants.find((x) => x.id === m.senderId);
    return (
      <article className="message" key={m.id}>
        <Avatar name={p?.name || m.senderName} agent={p?.kind === "agent"} />
        <div className="message-content">
          <div className="message-meta">
            <strong>{p?.name || m.senderName}</strong>
            {p?.kind === "agent" && (
              <span className="agent-tag">{p.provider || "Agent"}</span>
            )}
            <Time value={m.createdAt} />
          </div>
          {m.mentions.length > 0 && !m.body.includes("](#mention-all)") && (
            <div className="mentions">
              {m.mentions.filter((id) => !m.body.includes(`](#mention-${id})`)).map((id) => (
                <span key={id}>
                  @
                  {participants.find((x) => x.id === id)?.name ||
                    "Former member"}
                </span>
              ))}
            </div>
          )}
          <Markdown>{m.body}</Markdown>
          {m.docRefs?.map((ref) => (
            <button
              className="doc-reference"
              key={`${ref.docId}-${ref.revision}`}
              onClick={() => openDoc(ref)}
            >
              {ref.kind === "image" && <img className="message-image" src={imageUrl(channel.id, ref.docId, ref.revision)} alt={ref.title || "Attached image"} loading="lazy" />}
              ▤{" "}
              {ref.title ||
                docs.find((d) => d.id === ref.docId)?.title ||
                "Document"}{" "}
              · revision {ref.revision}
            </button>
          ))}
          {isRoot && (
            <button className="reply-link" onClick={() => openThread(m)}>
              Open thread
            </button>
          )}
        </div>
      </article>
    );
  }
  return (
    <>
      <header className="channel-header">
        <div>
          <div className="channel-title">
            <span className="hash">#</span>
            <h1>{channel.name}</h1>
            {channel.role === "owner" && (
              <span className="owner-badge">Owner</span>
            )}
            {channel.archived && <span className="owner-badge">Archived</span>}
          </div>
          <p>
            {participants.filter((p) => p.kind === "human").length} people,{" "}
            {participants.filter((p) => p.kind === "agent").length} agents{" "}
            <span className={`connection-dot ${connected ? "" : "offline"}`} />
            {connected ? "Connected" : "Reconnecting…"}
          </p>
        </div>
        <div className="header-actions">
          <button
            onClick={() => {
              setThread(null);
              threadId.current = null;
              setDocRef(undefined);
              setPanel(panel === "docs" ? null : "docs");
            }}
          >
            Docs <span>{docs.length}</span>
          </button>
          <button
            aria-label="Show participants"
            onClick={() => {
              setThread(null);
              threadId.current = null;
              setPanel(panel === "people" ? null : "people");
            }}
          >
            People
          </button>
          {channel.role === "owner" && (
            <button
              onClick={() => setInvite("human")}
              disabled={channel.archived}
            >
              Invite people
            </button>
          )}
          <button
            className="primary"
            onClick={() => setInvite("agent")}
            disabled={channel.archived}
          >
            Connect an agent
          </button>
          {channel.role === "owner" && (
            <button
              className="icon-button"
              aria-label="Manage channel"
              onClick={() => setManage(true)}
            >
              ···
            </button>
          )}
        </div>
      </header>
      <div className="channel-body">
        <section className="conversation" aria-label="Channel conversation">
          <div className="timeline">
            {loading ? (
              <p className="muted">Loading conversation…</p>
            ) : messages.length === 0 ? (
              <div className="channel-empty">
                <h2>{channel.archived ? "No messages yet" : "Start the conversation"}</h2>
                <p>{channel.archived ? "This channel is archived." : "Share a question, an idea, or a document."}</p>
              </div>
            ) : (
              messages.map((m) => messageView(m))
            )}
            <div ref={end} />
          </div>
          {error && <Notice>{error}</Notice>}
          <div className="composer-wrap">
            <Composer
              channelId={channel.id}
              userId={user.id}
              participants={participants}
              documents={docs}
              documentsChanged={() => void refreshDocs()}
              documentsOpening={() => setPanel(null)}
              disabled={channel.archived}
              sent={(m) => setMessages((v) => merge(v, [m]))}
            />
            <p className="composer-hint">
              Mention an agent or choose Ask all agents.{" "}
              <span>⌘ / Ctrl + Enter to send</span>
            </p>
          </div>
        </section>
        {thread && (
          <aside className="side-panel thread-panel">
            <header className="panel-header">
              <h2>Thread</h2>
              <button
                className="icon-button"
                aria-label="Close thread"
                onClick={() => {
                  setThread(null);
                  threadId.current = null;
                }}
              >
                ×
              </button>
            </header>
            <div className="thread-content">
              {messageView(thread, false)}
              <div className="thread-divider">Replies</div>
              {replies.map((m) => messageView(m, false))}
            </div>
            <div className="thread-compose">
              <Composer
                key={thread.id}
                channelId={channel.id}
                userId={user.id}
                rootId={thread.id}
                participants={participants}
                documents={docs}
                documentsChanged={() => void refreshDocs()}
                documentsOpening={() => setPanel(null)}
                disabled={channel.archived}
                sent={(m) => {
                  if (m.rootMessageId === threadId.current)
                    setReplies((v) => merge(v, [m]));
                }}
              />
            </div>
          </aside>
        )}
        {panel === "docs" && (
          <aside className="side-panel">
            <DocsPanel
              key={`${channel.id}-${docRef?.docId || ""}-${docRef?.revision || ""}`}
              userId={user.id}
              channelId={channel.id}
              documents={docs}
              initialRef={docRef}
              close={() => setPanel(null)}
              changed={() => void refreshDocs()}
              archived={channel.archived}
            />
          </aside>
        )}
        {panel === "people" && (
          <aside className="side-panel people-panel">
            <header className="panel-header">
              <h2>People & agents</h2>
              <button
                className="icon-button"
                aria-label="Close participants"
                onClick={() => setPanel(null)}
              >
                ×
              </button>
            </header>
            <p className="muted">
              Channel owned by{" "}
              {participants.find((p) => p.userId === channel.ownerId)?.name ||
                "a member"}
              .
            </p>
            {participants.map((p) => (
              <div className="person" key={p.id}>
                <Avatar name={p.name} agent={p.kind === "agent"} />
                <div>
                  <strong>{p.name}</strong>
                  <small>
                    {p.kind === "agent"
                      ? `${p.provider || "Agent"} · invited by ${participants.find((x) => x.id === p.invitedBy)?.name || "a member"}`
                      : p.userId === channel.ownerId
                        ? "Owner"
                        : "Member"}
                  </small>
                  {p.kind === "agent" && (
                    <small className={`presence ${p.presence}`}>
                      <i />
                      {p.presence === "waiting"
                        ? "Waiting"
                        : p.presence === "recent"
                          ? "Recently active"
                          : "Offline"}
                    </small>
                  )}
                  {p.kind === "agent" && !channel.archived &&
                    (channel.role === "owner" || p.invitedBy === self?.id) && (
                      <button className="reply-link" aria-label={`Rename ${p.name}`}
                        onClick={() => setRenaming(p)}>Rename</button>
                    )}
                </div>
                {p.userId !== channel.ownerId &&
                  (channel.role === "owner" ||
                    p.invitedBy === self?.id ||
                    p.id === self?.id) && (
                    <button className="quiet" onClick={() => void remove(p)}>
                      {p.id === self?.id ? "Leave" : "Remove"}
                    </button>
                  )}
              </div>
            ))}
            <p className="footnote">
              Agents listen while their existing session is active. Offline
              agents can catch up when they reconnect.
            </p>
          </aside>
        )}
      </div>
      {invite && (
        <InviteDialog
          channel={channel}
          kind={invite}
          userName={user.name}
          close={() => setInvite(null)}
        />
      )}{" "}
      {renaming && <RenameAgentDialog channelId={channel.id} participant={renaming}
        close={() => setRenaming(null)} changed={refreshPeople} />}
      {manage && (
        <ManageDialog
          channel={channel}
          participants={participants}
          close={() => setManage(false)}
          changed={refreshChannels}
        />
      )}
    </>
  );
}
