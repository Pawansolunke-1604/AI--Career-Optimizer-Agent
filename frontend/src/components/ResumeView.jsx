import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { downloadResumeDocx } from "../api";

export default function ResumeView({ markdown, sessionId }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function handleDownload() {
    setBusy(true);
    setError("");
    try {
      const blob = await downloadResumeDocx(sessionId);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "tailored-resume.docx";
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="resume-heading">
      <div className="results-bar">
        <h2 id="resume-heading">Tailored resume</h2>
        <button type="button" className="primary" onClick={handleDownload} disabled={busy}>
          {busy ? "Preparing…" : "Download .docx"}
        </button>
      </div>
      <p className="hint">
        Built only from facts in your resume and skills you confirmed in the chat. Read it through before you send it.
      </p>
      {error && <p className="error" role="alert">{error}</p>}
      <article className="paper markdown"><ReactMarkdown>{markdown}</ReactMarkdown></article>
    </section>
  );
}