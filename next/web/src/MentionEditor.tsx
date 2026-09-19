import { forwardRef, useEffect, useId, useImperativeHandle, useLayoutEffect, useRef, useState } from "react";
import type { Participant } from "./api";

export type InlineMention = { start: number; end: number; ids: string[]; all?: boolean };
export type MentionEditorHandle = { all: () => void; open: () => void };

// Preserve IDs only for untouched spans; editing/deleting a mention makes it
// ordinary text instead of leaving an invisible notification recipient behind.
type Edit = { before: string; start: number; end: number; type: string };
function editedMentions(before: string, after: string, mentions: InlineMention[], edit: Edit | null) {
  if (before === after) return mentions;
  // Autofill, undo, and unrecognized edits must never infer an identity from
  // identical display text. Keep their text, but require explicit reselection.
  if (!edit || edit.before !== before || edit.type.startsWith("history")) return [];
  let { start, end } = edit;
  if (start === end && edit.type.startsWith("delete")) {
    const removed = before.length - after.length;
    if (edit.type.endsWith("Backward")) start -= removed;
    else end += removed;
  }
  const inserted = after.length - before.length + end - start;
  if (start < 0 || inserted < 0 || before.slice(0, start) + after.slice(start, start + inserted) + before.slice(end) !== after) return [];
  const shift = after.length - before.length;
  return mentions.flatMap((m) => m.end <= start ? [m] : m.start >= end ? [{ ...m, start: m.start + shift, end: m.end + shift }] : []);
}

export function mentionBody(body: string, mentions: InlineMention[]) {
  let result = body;
  for (const m of [...mentions].sort((a, b) => b.start - a.start)) {
    const label = body.slice(m.start, m.end).replace(/([\\`*_{}\[\]()#+.!<>~-])/g, "\\$1");
    result = result.slice(0, m.start) + `[${label}](#mention-${m.all ? "all" : m.ids[0]})` + result.slice(m.end);
  }
  return result;
}

export const MentionEditor = forwardRef<MentionEditorHandle, {
  body: string; mentions: InlineMention[]; participants: Participant[];
  label: string; placeholder: string; disabled: boolean;
  change: (body: string, mentions: InlineMention[]) => void;
  send: () => void;
}>(function MentionEditor({ body, mentions, participants, label, placeholder, disabled, change, send }, ref) {
  const input = useRef<HTMLTextAreaElement>(null);
  const highlight = useRef<HTMLDivElement>(null);
  const edit = useRef<Edit | null>(null);
  const pendingCaret = useRef<number | null>(null);
  const listId = useId();
  const [cursor, setCursor] = useState(0);
  const [focused, setFocused] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const [selected, setSelected] = useState(0);
  const match = body.slice(0, cursor).match(/(?:^|\s)@([^@\n]{0,100})$/);
  const query = match?.[1].toLocaleLowerCase() ?? "";
  const start = match ? cursor - match[1].length - 1 : cursor;
  const inMention = mentions.some((m) => start >= m.start && start < m.end);
  const agents = participants.filter((p) => p.kind === "agent");
  const choices = [
    ...(agents.length && "all agents".includes(query) ? [{ key: "all", name: "All agents", detail: `${agents.length} agents · current recipients`, ids: agents.map((p) => p.id), all: true }] : []),
    ...participants.filter((p) => p.name.toLocaleLowerCase().includes(query)).map((p) => ({
      key: p.id, name: p.name.replace(/[\r\n]/g, " "), ids: [p.id], all: false,
      detail: p.kind === "agent" ? `${p.provider || "Agent"} · invited by ${participants.find((x) => x.id === p.invitedBy)?.name || "a member"}` : "Person",
    })),
  ];
  const open = focused && !!match && !inMention && !dismissed && !disabled;
  const active = Math.min(selected, Math.max(0, choices.length - 1));
  useEffect(() => {
    if (open) document.getElementById(`${listId}-${active}`)?.scrollIntoView({ block: "nearest" });
  }, [open, active, listId]);
  useLayoutEffect(() => {
    if (pendingCaret.current !== null) {
      const caret = pendingCaret.current;
      pendingCaret.current = null;
      input.current?.focus();
      input.current?.setSelectionRange(caret, caret);
    }
  });
  useEffect(() => {
    const textarea = input.current;
    const capture = (event: Event) => {
      if (textarea) edit.current = { before: textarea.value, start: textarea.selectionStart, end: textarea.selectionEnd, type: (event as InputEvent).inputType };
    };
    textarea?.addEventListener("beforeinput", capture);
    return () => textarea?.removeEventListener("beforeinput", capture);
  }, []);
  function place(text: string, spans: InlineMention[], caret: number) {
    pendingCaret.current = caret;
    change(text, spans);
    setCursor(caret);
    setDismissed(true);
  }
  function choose(choice: typeof choices[number], replaceQuery = true) {
    if (disabled) return;
    const from = replaceQuery && open ? start : (input.current?.selectionStart ?? body.length);
    const to = replaceQuery && open ? cursor : (input.current?.selectionEnd ?? from);
    const label = `@${choice.name}`;
    const insertion = `${from && !/\s/.test(body[from - 1]) ? " " : ""}${label} `;
    const next = body.slice(0, from) + insertion + body.slice(to);
    const adjusted = mentions.flatMap((m) => m.end <= from ? [m] : m.start >= to ? [{ ...m, start: m.start + insertion.length - (to - from), end: m.end + insertion.length - (to - from) }] : []);
    const tokenStart = from + insertion.length - label.length - 1;
    place(next, [...adjusted, { start: tokenStart, end: tokenStart + label.length, ids: choice.ids, all: choice.all }].sort((a, b) => a.start - b.start), from + insertion.length);
  }
  useImperativeHandle(ref, () => ({
    all: () => { if (agents.length) choose({ key: "all", name: "All agents", detail: "", ids: agents.map((p) => p.id), all: true }, false); },
    open: () => {
      const pos = input.current?.selectionStart ?? body.length;
      const insertion = `${pos && !/\s/.test(body[pos - 1]) ? " " : ""}@`;
      const next = body.slice(0, pos) + insertion + body.slice(pos);
      place(next, editedMentions(body, next, mentions, { before: body, start: pos, end: pos, type: "insertText" }), pos + insertion.length);
      setDismissed(false); setSelected(0);
    },
  }));
  const parts = [];
  let offset = 0;
  for (const m of mentions) {
    parts.push(body.slice(offset, m.start));
    parts.push(<span className="mention-highlight" key={`${m.start}-${m.end}`}>{body.slice(m.start, m.end)}</span>);
    offset = m.end;
  }
  parts.push(body.slice(offset), "\n");
  return <div className="mention-editor">
    <div className="mention-backdrop" ref={highlight} aria-hidden="true">{parts}</div>
    <textarea ref={input} aria-label={label} placeholder={placeholder} value={body} disabled={disabled}
      aria-autocomplete="list" aria-controls={open ? listId : undefined}
      aria-activedescendant={open && choices.length ? `${listId}-${active}` : undefined}
      onFocus={() => setFocused(true)} onBlur={() => setFocused(false)}
      onSelect={(e) => setCursor(e.currentTarget.selectionStart)}
      onScroll={(e) => { if (highlight.current) { highlight.current.scrollTop = e.currentTarget.scrollTop; highlight.current.scrollLeft = e.currentTarget.scrollLeft; } }}
      onChange={(e) => { change(e.target.value, editedMentions(body, e.target.value, mentions, edit.current)); edit.current = null; setCursor(e.target.selectionStart); setDismissed(false); setSelected(0); }}
      onKeyDown={(e) => {
        if (e.nativeEvent.isComposing) return;
        if (open && ["ArrowDown", "ArrowUp"].includes(e.key)) {
          e.preventDefault(); setSelected((active + (e.key === "ArrowDown" ? 1 : -1) + choices.length) % Math.max(1, choices.length));
        } else if (open && e.key === "Enter" && !e.ctrlKey && !e.metaKey && choices.length) {
          e.preventDefault(); choose(choices[active]);
        } else if (open && e.key === "Escape") { e.preventDefault(); setDismissed(true); }
        else if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); send(); }
      }} />
    {open && <div className="mention-menu" id={listId} role="listbox" aria-label="Mention suggestions">
      {choices.length ? choices.map((choice, i) => <button type="button" role="option" tabIndex={-1}
        id={`${listId}-${i}`} key={choice.key} aria-selected={i === active}
        onMouseDown={(e) => e.preventDefault()} onClick={() => choose(choice)}>
        <strong>{choice.name}</strong><small>{choice.detail}</small>
      </button>) : <div className="mention-empty" role="status">No matching participants</div>}
    </div>}
  </div>;
});
