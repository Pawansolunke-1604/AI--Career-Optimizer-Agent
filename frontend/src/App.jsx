import { useState } from "react";
import { analyzeResume } from "./api";
import usePersistentState from "./usePersistentState";
import UploadForm from "./components/UploadForm";
import ScoreCard from "./components/ScoreCard";
import SkillGroups from "./components/SkillGroups";
import Report from "./components/Report";
import Chat from "./components/Chat";
import ResumeView from "./components/ResumeView";

export default function App() {
  // These three survive a page refresh. result.session_id is how the backend recognises this user.
  const [result, setResult] = usePersistentState("analysis", null);
  const [messages, setMessages] = usePersistentState("messages", []);
  const [resumeMarkdown, setResumeMarkdown] = usePersistentState("resumeMarkdown", null);

  const [tab, setTab] = useState("analysis");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleAnalyze(file, jdText) {
    setLoading(true);
    setError("");
    try {
      const data = await analyzeResume(file, jdText);
      setMessages([]); // a new analysis is a new conversation
      setResumeMarkdown(null);
      setTab("analysis");
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function startOver() {
    setResult(null);
    setMessages([]);
    setResumeMarkdown(null);
    setError("");
  }

  const tabs = [
    { id: "analysis", label: "Analysis" },
    { id: "chat", label: "Ask the assistant" },
    ...(resumeMarkdown ? [{ id: "resume", label: "Tailored resume" }] : []),
  ];

  return (
    <div className="page">
      <header className="masthead">
        <h1>Resume Match</h1>
        <p>See how your resume fits a job, what is missing, and how to close the gap.</p>
      </header>

      {!result && (
        <main>
          <UploadForm onSubmit={handleAnalyze} loading={loading} />
          {error && <p className="error" role="alert">{error}</p>}
        </main>
      )}

      {result && (
        <main className="results">
          <div className="results-bar">
            <h2>Your results</h2>
            <button type="button" className="secondary" onClick={startOver}>Check another resume</button>
          </div>

          <div className="tabs" role="tablist" aria-label="Sections">
            {tabs.map((t) => (
              <button
                key={t.id}
                type="button"
                role="tab"
                id={`tab-${t.id}`}
                aria-selected={tab === t.id}
                aria-controls={`panel-${t.id}`}
                className={`tab${tab === t.id ? " is-active" : ""}`}
                onClick={() => setTab(t.id)}
              >
                {t.label}
              </button>
            ))}
          </div>

          <div role="tabpanel" id="panel-analysis" aria-labelledby="tab-analysis" hidden={tab !== "analysis"} className="stack">
            <ScoreCard match={result.match} />
            <SkillGroups match={result.match} />
            <Report report={result.report} error={result.report_error} />
          </div>

          {/* Kept mounted (just hidden) so a half-typed message is not lost when switching tabs. */}
          <div role="tabpanel" id="panel-chat" aria-labelledby="tab-chat" hidden={tab !== "chat"}>
            <Chat
              sessionId={result.session_id}
              messages={messages}
              setMessages={setMessages}
              onResume={setResumeMarkdown}
              onOpenResume={() => setTab("resume")}
              onExpired={startOver}
            />
          </div>

          {resumeMarkdown && (
            <div role="tabpanel" id="panel-resume" aria-labelledby="tab-resume" hidden={tab !== "resume"}>
              <ResumeView markdown={resumeMarkdown} sessionId={result.session_id} />
            </div>
          )}
        </main>
      )}
    </div>
  );
}