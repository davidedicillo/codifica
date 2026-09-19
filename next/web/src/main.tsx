import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  api,
  post,
  uid,
  errorText,
  setCsrf,
  type User,
  type Channel,
} from "./api";
import { Brand, Avatar, Modal, Notice } from "./ui";
import { ChannelPage } from "./ChannelPage";
import "./styles.css";
function App() {
  const [user, setUser] = useState<User | null>(null),
    [ready, setReady] = useState(false),
    [dev, setDev] = useState(false),
    [emailAuth, setEmailAuth] = useState(false),
    [codeSent, setCodeSent] = useState(false),
    [code, setCode] = useState(""),
    [loginUrl, setLoginUrl] = useState("/api/v1/auth/login"),
    [email, setEmail] = useState(""),
    [name, setName] = useState(""),
    [error, setError] = useState(""),
    [channels, setChannels] = useState<Channel[]>([]),
    [active, setActive] = useState<string | null>(() =>
      sessionStorage.getItem("codifica:active"),
    ),
    [create, setCreate] = useState(false),
    [channelName, setChannelName] = useState(""),
    [busy, setBusy] = useState(false),
    [invite, setInvite] = useState<{
      channelName: string;
      kind: string;
      email?: string;
      expiresAt: string;
    } | null>(null);
  useEffect(() => {
    if (active) sessionStorage.setItem("codifica:active", active);
  }, [active]);
  const invitation = location.pathname.match(/^\/i\/([^/]+)/)?.[1];
  async function refreshChannels() {
    try {
      const r = await api<{ channels: Channel[] }>("/channels");
      setChannels(r.channels);
      setActive((id) =>
        r.channels.some((c) => c.id === id) ? id : r.channels[0]?.id || null,
      );
    } catch (e) {
      setError(errorText(e));
    }
  }
  async function loadSession() {
    try {
      const r = await api<{ user: User; csrfToken: string }>("/me");
      setUser(r.user);
      setCsrf(r.csrfToken);
      await refreshChannels();
    } catch {
      setUser(null);
    } finally {
      setReady(true);
    }
  }
  useEffect(() => {
    void loadSession();
    void api<{ devAuth: boolean; emailAuth: boolean; loginUrl: string }>("/auth/config")
      .then((r) => {
        setDev(r.devAuth);
        setEmailAuth(r.emailAuth);
        setLoginUrl(r.loginUrl);
      })
      .catch(() => {});
    if (invitation)
      void api<{
        channelName: string;
        kind: string;
        email?: string;
        expiresAt: string;
      }>(`/invites/${invitation}`)
        .then(setInvite)
        .catch((e) => setError(errorText(e)));
  }, []);
  async function login() {
    setBusy(true);
    setError("");
    try {
      if (emailAuth && !codeSent) {
        await post("/auth/email/request", { email });
        setCodeSent(true);
        return;
      }
      if (emailAuth) await post("/auth/email/verify", { code, name });
      else await post("/auth/dev-login", { email, name });
      setCodeSent(false);
      setCode("");
      await loadSession();
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  async function join() {
    if (!invitation) return;
    setBusy(true);
    setError("");
    try {
      const r = await post<{ channelId: string }>(
        `/invites/${invitation}/join`,
        {
          requestId:
            sessionStorage.getItem(`join:${invitation}`) ||
            (() => {
              const id = uid();
              sessionStorage.setItem(`join:${invitation}`, id);
              return id;
            })(),
        },
      );
      history.replaceState(null, "", "/");
      setInvite(null);
      await refreshChannels();
      setActive(r.channelId);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  async function newChannel() {
    setBusy(true);
    setError("");
    try {
      const c = await post<Channel>("/channels", { name: channelName });
      setCreate(false);
      setChannelName("");
      await refreshChannels();
      setActive(c.id);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  if (!ready)
    return (
      <div className="loading">
        <Brand />
        <p>Opening your workspace…</p>
      </div>
    );
  if (!user)
    return (
      <main className="login-page">
        <div className="login-story">
          <Brand />
          <div>
            <span className="conversation-glyph" aria-hidden="true">
              “
            </span>
            <h1>
              Good work starts
              <br />
              with a conversation.
            </h1>
            <p>
              A shared space for you, your collaborators, and the coding agents
              you already use.
            </p>
          </div>
          <footer>Your people. Your agents. One conversation.</footer>
        </div>
        <section className="login-form">
          <div>
            <h2>
              {invite ? `Join ${invite.channelName}` : "Welcome to Codifica"}
            </h2>
            <p className="muted">
              {invite
                ? "Sign in to accept your invitation. Members can read the full channel history and shared docs."
                : "Bring your own agents. Keep everyone in the conversation."}
            </p>
            {dev || emailAuth ? (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  void login();
                }}
              >
                {!emailAuth && <div className="dev-label">Local development sign-in</div>}
                {codeSent && <p className="muted">If this email has access, a sign-in code is on its way.</p>}
                <label>
                  Your name
                  <input
                    autoComplete="name"
                    required
                    value={name}
                    maxLength={100}
                    disabled={busy || codeSent}
                    onChange={(e) => setName(e.target.value)}
                  />
                </label>
                <label>
                  Email address
                  <input
                    type="email"
                    autoComplete="email"
                    required
                    value={email}
                    disabled={busy || codeSent}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                </label>
                {codeSent && <label>Sign-in code
                  <input autoComplete="one-time-code" inputMode="numeric" pattern="[0-9]{6}" maxLength={6} required value={code} onChange={e => setCode(e.target.value)} />
                </label>}
                <button className="primary wide" disabled={busy}>
                  {busy ? "Please wait…" : emailAuth ? (codeSent ? "Sign in" : "Send sign-in code") : "Continue"}
                </button>
                {codeSent && <button type="button" className="wide" disabled={busy} onClick={() => { setCodeSent(false); setCode(""); setError(""); }}>Use a different email</button>}
                {codeSent && <p className="footnote">Codes expire after 10 minutes. To resend, go back and request another code after one minute.</p>}
              </form>
            ) : (
              <a
                className="button primary wide"
                href={`${loginUrl}${invitation ? `?invite=${encodeURIComponent(invitation)}` : ""}`}
              >
                Sign in
              </a>
            )}
            {error && <Notice>{error}</Notice>}
            <p className="footnote">Private channels, by invitation.</p>
          </div>
        </section>
      </main>
    );
  const selected = channels.find((c) => c.id === active);
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Brand />
        <div className="sidebar-heading">
          <span>Channels</span>
          <button
            className="icon-button"
            aria-label="Create channel"
            onClick={() => setCreate(true)}
          >
            +
          </button>
        </div>
        <nav aria-label="Channels">
          {channels.length === 0 && (
            <p className="muted sidebar-empty">
              Your conversations will live here.
            </p>
          )}
          {channels.map((c) => (
            <button
              className={`channel-item ${c.id === active ? "selected" : ""}`}
              key={c.id}
              onClick={() => {
                setActive(c.id);
                setError("");
              }}
            >
              <span className="hash">#</span>
              <span>{c.name}</span>
              {c.role === "owner" && <small>Owner</small>}
              {c.archived && <small>Archived</small>}
            </button>
          ))}
        </nav>
        <div className="sidebar-note">
          <span className="orbit-icon">✳</span>
          <p>
            Different agents.
            <br />
            Shared understanding.
          </p>
        </div>
        <div className="account">
          <Avatar name={user.name} />
          <div>
            <strong>{user.name}</strong>
            <small>{user.email}</small>
          </div>
          <button
            className="icon-button"
            aria-label="Sign out"
            onClick={() => {
              void post("/auth/logout", {})
                .then(() => {
                  setUser(null);
                  setCsrf("");
                  for (const key of Object.keys(sessionStorage)) {
                    if (key.startsWith("codifica:"))
                      sessionStorage.removeItem(key);
                  }
                  setActive(null);
                })
                .catch((e) => setError(errorText(e)));
            }}
          >
            ↪
          </button>
        </div>
      </aside>
      <main className="workspace">
        {error && <Notice>{error}</Notice>}
        {invite ? (
          <div className="invitation-page">
            <h1>You’re invited to {invite.channelName}</h1>
            <p>
              Joining gives you access to the full conversation history and all
              shared document revisions.
            </p>
            {invite.kind === "agent" ? (
              <p>
                This is an agent invitation. Paste its instructions link into
                your coding agent.
              </p>
            ) : (
              <>
                <p>
                  Invitation for {invite.email}. Signed in as {user.email}.
                </p>
                <button
                  className="primary"
                  disabled={busy}
                  onClick={() => void join()}
                >
                  {busy ? "Joining…" : "Join channel"}
                </button>
              </>
            )}
          </div>
        ) : selected ? (
          <ChannelPage
            key={selected.id}
            channel={selected}
            user={user}
            refreshChannels={() => void refreshChannels()}
          />
        ) : (
          <div className="empty-state welcome">
            <span className="empty-symbol">✳</span>
            <h1>Make room for a good idea.</h1>
            <p>
              Create a channel, invite a collaborator, and connect the agents
              you already work with.
            </p>
            <button className="primary" onClick={() => setCreate(true)}>
              Create your first channel
            </button>
          </div>
        )}
      </main>
      {create && (
        <Modal title="Create a channel" close={() => setCreate(false)}>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void newChannel();
            }}
          >
            <label>
              Channel name
              <input
                autoFocus
                required
                maxLength={80}
                placeholder="e.g. the-next-idea"
                value={channelName}
                onChange={(e) => setChannelName(e.target.value)}
              />
            </label>
            <p className="muted">
              You’ll own this channel. Invite people when you’re ready.
            </p>
            <button className="primary" disabled={busy || !channelName.trim()}>
              {busy ? "Creating…" : "Create channel"}
            </button>
            {error && <Notice>{error}</Notice>}
          </form>
        </Modal>
      )}
    </div>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
