// All calls to the FastAPI backend live here, so components never deal with fetch details.
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status; // 0 = server unreachable
  }
}

async function send(path, options) {
  let response;
  try {
    response = await fetch(`${API_URL}${path}`, options);
  } catch {
    throw new ApiError("Cannot reach the server. Check that the backend is running.", 0);
  }
  if (!response.ok) {
    let message = `Something went wrong (error ${response.status}).`;
    try {
      const body = await response.json();
      if (body.error) message = body.error; // our own AppError format
      else if (body.detail) message = "The request was not accepted. Please check your input and try again.";
    } catch {
      /* keep the default message */
    }
    throw new ApiError(message, response.status);
  }
  return response;
}

export async function analyzeResume(file, jdText) {
  const form = new FormData();
  form.append("file", file);
  form.append("jd_text", jdText);
  const response = await send("/analysis/analyze", { method: "POST", body: form });
  return response.json();
}

// The session_id is how the backend knows whose resume and analysis this message belongs to.
export async function sendChatMessage(sessionId, message) {
  const response = await send("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message }),
  });
  return response.json();
}

export async function downloadResumeDocx(sessionId) {
  const response = await send(`/resumes/${sessionId}/docx`);
  return response.blob();
}