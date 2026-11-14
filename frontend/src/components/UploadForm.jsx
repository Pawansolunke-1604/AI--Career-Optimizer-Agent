import { useRef, useState } from "react";

const MAX_MB = 5; // keep in sync with MAX_UPLOAD_MB in the backend .env
const MIN_JD_CHARS = 50;

export default function UploadForm({ onSubmit, loading }) {
  const [file, setFile] = useState(null);
  const [jdText, setJdText] = useState("");
  const [dragging, setDragging] = useState(false);
  const [fileError, setFileError] = useState("");
  const inputRef = useRef(null);

  function pickFile(candidate) {
    if (!candidate) return;
    const name = candidate.name.toLowerCase();
    if (!name.endsWith(".pdf") && !name.endsWith(".docx")) {
      setFileError("Upload a PDF or DOCX file.");
      return;
    }
    if (candidate.size > MAX_MB * 1024 * 1024) {
      setFileError(`The file is larger than ${MAX_MB} MB.`);
      return;
    }
    setFileError("");
    setFile(candidate);
  }

  const jdReady = jdText.trim().length >= MIN_JD_CHARS;
  const canSubmit = file && jdReady && !loading;

  function handleSubmit(event) {
    event.preventDefault();
    if (canSubmit) onSubmit(file, jdText.trim());
  }

  return (
    <form className="upload" onSubmit={handleSubmit}>
      <div className="field">
        <label className="field-label" htmlFor="resume-file">Your resume</label>
        <div
          className={`dropzone${dragging ? " is-dragging" : ""}${file ? " has-file" : ""}`}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => { e.preventDefault(); setDragging(false); pickFile(e.dataTransfer.files[0]); }}
        >
          <input
            ref={inputRef}
            id="resume-file"
            type="file"
            accept=".pdf,.docx"
            className="visually-hidden"
            onChange={(e) => pickFile(e.target.files[0])}
          />
          {file ? (
            <>
              <span className="file-name">{file.name}</span>
              <span className="hint">{(file.size / 1024).toFixed(0)} KB</span>
              <button type="button" className="link-button" onClick={() => inputRef.current.click()}>
                Choose a different file
              </button>
            </>
          ) : (
            <>
              <span className="drop-title">Drop your resume here</span>
              <span className="hint">PDF or DOCX, up to {MAX_MB} MB</span>
              <button type="button" className="secondary" onClick={() => inputRef.current.click()}>
                Browse files
              </button>
            </>
          )}
        </div>
        {fileError && <p className="field-error" role="alert">{fileError}</p>}
      </div>

      <div className="field">
        <label className="field-label" htmlFor="jd-text">Job description</label>
        <textarea
          id="jd-text"
          value={jdText}
          onChange={(e) => setJdText(e.target.value)}
          placeholder="Paste the full job description, including requirements and preferred skills."
          rows={10}
        />
        <p className="hint">
          {jdText.trim().length === 0
            ? "Paste the whole posting for the best result."
            : jdReady
              ? `${jdText.trim().length} characters`
              : `Add a little more: ${MIN_JD_CHARS - jdText.trim().length} more characters needed.`}
        </p>
      </div>

      <div className="actions">
        <button type="submit" className="primary" disabled={!canSubmit}>
          {loading ? "Analyzing…" : "Check my match"}
        </button>
        {loading && <p className="hint" role="status">This takes about 30 to 60 seconds. Please keep this tab open.</p>}
      </div>
    </form>
  );
}