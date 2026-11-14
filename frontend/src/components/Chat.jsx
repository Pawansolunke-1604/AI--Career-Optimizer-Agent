import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { sendChatMessage } from "../api";

const SUGGESTIONS = [
  "Why is my score not higher?",
  "What would my score be if I learned Docker and AWS?",
  "Rewrite my strongest project bullet for this job",
  "Create a tailored resume for this job",
];

// Plain-language names for what the assistant did behind the scenes.
const TOOL_LABELS = {
  get_analysis_overview: "checked your analysis",
  explain_gap: "looked at a skill gap",
  find_resume_evidence: "searched your resume",
  simulate_score: "ran a what-if score",
  rewrite_resume_bullet: "rewrote a bullet",
  confirm_skill: "saved a skill you confirmed",
  generate_optimized_resume: "built a tailored resume",
};

export default function Chat({ sessionId, messages, setMessages, onResume, onOpenResume, onExpired }) {
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [expired, setExpired] = useState(false);
  const listRef = useRef(null);

  useEffect(() => {
    const list = listRef.current;
    if (list) list.scrollTop = list.scrollHeight;
  }, [messages, sending]);

  async function send(text) {
    const message = text.trim();
    if (!message || sending) return;
    setMessages((all) => [...all, { role: "user", text: message }]);
    setDraft("");
    setSending(true);
    try {
      const data = await sendChatMessage(sessionId, message);
      setMessages((all) => [
        ...all,
        { role: "assistant", text: data.reply, tools: data.tools_used, hasResume: Boolean(data.resume_markdown) },
      ]);
      if (data.resume_markdown) onResume(data.resume_markdown);
    } catch (err) {
      if (err.status === 404) setExpired(true); // the backend no longer has this session
      setMessages((all) => [...all, { role: "error", text: err.message }]);
    } finally {
      setSending(false);
    }
  }

  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      send(draft);
    }
  }

  return (
    <section className="chat" aria-label="Chat with the assistant">
      <div className="chat-list" ref={listRef}>
        {messages.length === 0 && (
          <div className="chat-empty">
            <p>Ask about your score, a missing skill, or a bullet point. Try one of these:</p>
            <ul className="chips">
              {SUGGESTIONS.map((s) => (
                <li key={s}>
                  <button type="button" className="suggestion" onClick={() => send(s)} disabled={sending || expired}>
                    {s}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={`msg msg-${m.role}`}>
            {m.role === "assistant" ? (
              <>
                <div className="markdown"><ReactMarkdown>{m.text}</ReactMarkdown></div>
                {m.tools?.length > 0 && (
                  <p className="msg-meta">
                    Used: {[...new Set(m.tools)].map((t) => TOOL_LABELS[t] || t).join(", ")}
                  </p>
                )}
                {m.hasResume && (
                  <button type="button" className="secondary small" onClick={onOpenResume}>
                    Open tailored resume
                  </button>
                )}
              </>
            ) : (
              <p>{m.text}</p>
            )}
          </div>
        ))}

        {sending && <p className="msg-status" role="status">The assistant is working on it…</p>}
      </div>

      {expired ? (
        <div className="notice">
          This session has expired, so the assistant no longer has your resume.{" "}
          <button type="button" className="link-button" onClick={onExpired}>Check your resume again</button>
        </div>
      ) : (
        <form className="chat-form" onSubmit={(e) => { e.preventDefault(); send(draft); }}>
          <label htmlFor="chat-input" className="visually-hidden">Your message</label>
          <textarea
            id="chat-input"
            rows={2}
            maxLength={2000}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question. Enter sends, Shift+Enter adds a new line."
            disabled={sending}
          />
          <button type="submit" className="primary" disabled={sending || !draft.trim()}>Send</button>
        </form>
      )}
    </section>
  );
}