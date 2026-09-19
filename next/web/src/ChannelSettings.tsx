import { useEffect, useState } from "react";
import {
  api,
  post,
  patch,
  errorText,
  type Channel,
  type Participant,
  type Invite,
} from "./api";
import { Modal, Notice } from "./ui";
export function InviteDialog({
  channel,
  kind,
  close,
}: {
  channel: Channel;
  kind: "human" | "agent";
  close: () => void;
}) {
  const [email, setEmail] = useState(""),
    [link, setLink] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [copied, setCopied] = useState(false);
  async function create() {
    setBusy(true);
    setError("");
    try {
      const r = await post<{ url: string; instructionsUrl: string }>(
        `/channels/${channel.id}/invites`,
        { kind, ...(kind === "human" ? { email } : {}) },
      );
      setLink(
        kind === "agent"
          ? `Join my Codifica channel. Read the instructions at ${r.instructionsUrl} and participate from this session. Listen for messages while this session remains active.`
          : r.url,
      );
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal
      title={kind === "human" ? "Invite a person" : "Connect your agent"}
      close={close}
    >
      <p>
        {kind === "human"
          ? "They’ll have access to the full conversation history and all shared document revisions."
          : "Use Codex, Claude, or another agent you already run. Paste the invitation into its existing session."}
      </p>
      {!link ? (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void create();
          }}
        >
          {kind === "human" && (
            <label>
              Email address
              <input
                type="email"
                autoFocus
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </label>
          )}
          <p className="muted">One use. Expires in seven days.</p>
          <button className="primary" disabled={busy}>
            {busy
              ? "Creating…"
              : kind === "human"
                ? "Create invitation"
                : "Create connection prompt"}
          </button>
        </form>
      ) : (
        <>
          <label>
            {kind === "human"
              ? "Invitation link"
              : "Paste this into your agent"}
            <textarea className="invite-text" readOnly value={link} />
          </label>
          <button
            className="primary"
            onClick={() => {
              void navigator.clipboard
                .writeText(link)
                .then(() => setCopied(true))
                .catch(() =>
                  setError("Copy failed. Select and copy the text above."),
                );
            }}
          >
            {copied ? "Copied" : "Copy invitation"}
          </button>
          {kind === "agent" && (
            <p className="muted">
              Listening depends on your agent session staying active. Your
              private chat history is not uploaded.
            </p>
          )}
        </>
      )}
      {error && <Notice>{error}</Notice>}
    </Modal>
  );
}
export function ManageDialog({
  channel,
  participants,
  close,
  changed,
}: {
  channel: Channel;
  participants: Participant[];
  close: () => void;
  changed: () => void;
}) {
  const [name, setName] = useState(channel.name),
    [newOwner, setNewOwner] = useState(""),
    [invites, setInvites] = useState<Invite[]>([]),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function refresh() {
    try {
      setInvites(
        (await api<{ invites: Invite[] }>(`/channels/${channel.id}/invites`))
          .invites,
      );
    } catch (e) {
      setError(errorText(e));
    }
  }
  useEffect(() => {
    void refresh();
  }, []);
  async function change(body: object) {
    setBusy(true);
    try {
      await patch(`/channels/${channel.id}`, body);
      changed();
      close();
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal title="Manage channel" close={close}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void change({ name });
        }}
      >
        <label>
          Channel name
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
        </label>
        <button disabled={busy || !name.trim()} className="primary">
          Save name
        </button>
      </form>
      <hr />
      <h3>Ownership</h3>
      <p className="muted">Transfer control to another human member.</p>
      <select
        aria-label="New owner"
        value={newOwner}
        onChange={(e) => setNewOwner(e.target.value)}
      >
        <option value="">Choose a member</option>
        {participants
          .filter((p) => p.kind === "human" && p.userId !== channel.ownerId)
          .map((p) => (
            <option key={p.id} value={p.userId!}>
              {p.name}
            </option>
          ))}
      </select>
      <button
        disabled={busy || !newOwner}
        onClick={() => {
          if (
            window.confirm(
              "Transfer channel ownership? You will become a member.",
            )
          )
            void change({ ownerId: newOwner });
        }}
      >
        Transfer ownership
      </button>
      <hr />
      <h3>Invitations</h3>
      {invites.length === 0 && <p className="muted">No invitations yet.</p>}
      {invites.map((i) => (
        <div className="invite-row" key={i.id}>
          <span>
            {i.email || "Agent invitation"}
            <small>
              {i.revoked
                ? "Revoked"
                : i.used
                  ? "Used"
                  : new Date(i.expiresAt).getTime() < Date.now()
                    ? "Expired"
                    : "Pending"}
            </small>
          </span>
          {!i.revoked && !i.used && (
            <button
              onClick={() => {
                void api(`/channels/${channel.id}/invites/${i.id}`, {
                  method: "DELETE",
                })
                  .then(refresh)
                  .catch((e) => setError(errorText(e)));
              }}
            >
              Revoke
            </button>
          )}
        </div>
      ))}
      <hr />
      <h3>{channel.archived ? "Restore conversation" : "Archive channel"}</h3>
      <p className="muted">
        Archived channels retain their history and documents and become
        read-only.
      </p>
      <button
        disabled={busy}
        onClick={() => void change({ archived: !channel.archived })}
      >
        {channel.archived ? "Restore channel" : "Archive channel"}
      </button>
      {error && <Notice>{error}</Notice>}
    </Modal>
  );
}
