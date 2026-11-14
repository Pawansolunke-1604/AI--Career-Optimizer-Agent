"""Accuracy report for the career agent.

Run from the backend folder:
    python -m evaluation.run_eval             full run (about 10 Gemini calls, ~2 minutes)
    python -m evaluation.run_eval --offline   guardrail checks only (no Gemini calls)
    python -m evaluation.run_eval --no-report skip the strengths/gaps report calls (5 fewer calls)
The result is printed and saved to evaluation/report.md.
"""
import argparse
import re
import time
from datetime import datetime
from pathlib import Path

from app.core.exceptions import InputRejectedError
from app.schemas.job_description import JobDescriptionData
from app.schemas.resume import Experience, ResumeData
from app.services import guardrails
from app.services.scoring_service import calculate_experience_years, compute_match
from app.utils.skill_normalizer import is_grounded, is_literally_present, normalize_skills
from evaluation.cases import CASES, GUARDRAIL_CASES, JDS, PAIRS, RESUMES

REPORT_PATH = Path(__file__).parent / "report.md"
NUMBER = re.compile(r"\d+(?:\.\d+)?")


# ---------- small helpers ----------

def keys(skills: list[str]) -> set[str]:
    return set(normalize_skills(skills))  # canonical lowercase names, so "MySQL" == "SQL" family


def prf(expected: list[str], got: list[str]) -> tuple[float, float, float]:
    exp, got_k = keys(expected), keys(got)
    tp = len(exp & got_k)
    precision = tp / len(got_k) if got_k else 0.0
    recall = tp / len(exp) if exp else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def to_experience(spans: list[tuple[str, str]]) -> list[Experience]:
    return [Experience(company="Ref", role="Ref", start_date=s, end_date=e) for s, e in spans]


def pct(x: float) -> str:
    return f"{x * 100:.0f}%"


def avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def md_table(headers: list[str], rows: list[list]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(lines)


# ---------- 1. guardrails (no LLM) ----------

def run_guardrails() -> dict:
    rows, passed = [], 0
    for name, kind, text, expected in GUARDRAIL_CASES:
        try:
            if kind == "resume":
                guardrails.validate_resume_text(text)
                got = "accept"
            elif kind == "jd":
                guardrails.validate_jd_text(text)
                got = "accept"
            elif kind == "document":
                _, removed = guardrails.sanitize_document(text, "resume")
                got = f"removed:{removed}"
            else:
                guardrails.check_chat_message(text)
                got = "accept"
        except InputRejectedError:
            got = "reject"
        ok = got == expected
        passed += ok
        rows.append([name, expected, got, "PASS" if ok else "FAIL"])
    return {"rows": rows, "passed": passed, "total": len(GUARDRAIL_CASES)}


# ---------- 2. extraction, scoring, report (calls Gemini) ----------

def run_llm_parts(args) -> dict:
    from app.agents.tools.gap_analysis_tool import generate_report
    from app.agents.tools.jd_parser_tool import extract_jd_data
    from app.agents.tools.resume_parser_tool import extract_resume_data

    def call(fn, *a):
        try:
            return fn(*a)
        except Exception as exc:  # keep going; a failed call is reported, not fatal
            print(f"   ! call failed: {getattr(exc, 'message', exc)}")
            return None
        finally:
            time.sleep(args.pause)

    out = {"resume_rows": [], "jd_rows": [], "case_rows": [], "pair_rows": [], "report_rows": [],
           "resume_f1": [], "resume_recall": [], "resume_precision": [], "year_errors": [],
           "invented_skills": 0, "jd_required_recall": [], "jd_required_precision": [],
           "jd_preferred_recall": [], "in_band": 0, "cases_done": 0, "pairs_ok": 0,
           "unsupported_matches": 0, "false_gaps": 0, "evidence": [], "unverified_numbers": 0,
           "reports_done": 0, "failed_calls": 0}

    resumes, jds = {}, {}
    for rid, r in RESUMES.items():
        print(f"Extracting resume: {rid}")
        data = call(extract_resume_data, r["text"])
        if data is None:
            out["failed_calls"] += 1
            continue
        resumes[rid] = data
        p, rec, f1 = prf(r["skills"], data.skills)
        invented = [s for s in data.skills if not is_grounded(s, r["text"].lower())]
        want = calculate_experience_years(to_experience(r["experience"]))
        got = calculate_experience_years(data.experience)
        out["resume_f1"].append(f1)
        out["resume_recall"].append(rec)
        out["resume_precision"].append(p)
        out["year_errors"].append(abs(want - got))
        out["invented_skills"] += len(invented)
        missed = sorted(keys(r["skills"]) - keys(data.skills))
        extra = sorted(keys(data.skills) - keys(r["skills"]))
        out["resume_rows"].append([rid, pct(p), pct(rec), pct(f1), f"{want} / {got}",
                                   ", ".join(missed) or "-", ", ".join(extra) or "-",
                                   ", ".join(invented) or "-"])

    for jid, j in JDS.items():
        print(f"Extracting job description: {jid}")
        data = call(extract_jd_data, j["text"])
        if data is None:
            out["failed_calls"] += 1
            continue
        jds[jid] = data
        rp, rr, _ = prf(j["required"], data.required_skills)
        _, pr, _ = prf(j["preferred"], data.preferred_skills)
        out["jd_required_precision"].append(rp)
        out["jd_required_recall"].append(rr)
        out["jd_preferred_recall"].append(pr)
        missed = sorted(keys(j["required"]) - keys(data.required_skills))
        out["jd_rows"].append([jid, pct(rp), pct(rr), pct(pr), ", ".join(missed) or "-"])

    scores = {}
    for case_id, rid, jid, (lo, hi) in CASES:
        if rid not in resumes or jid not in jds:
            continue
        text = RESUMES[rid]["text"]
        match = compute_match(resumes[rid], jds[jid], text)
        ref = compute_match(
            ResumeData(skills=RESUMES[rid]["skills"], experience=to_experience(RESUMES[rid]["experience"])),
            JobDescriptionData(required_skills=JDS[jid]["required"], preferred_skills=JDS[jid]["preferred"],
                               min_experience_years=JDS[jid]["min_years"]),
            text)
        scores[case_id] = match.overall_score
        in_band = lo <= match.overall_score <= hi
        out["in_band"] += in_band
        out["cases_done"] += 1
        matched = match.required.matched + match.preferred.matched + match.keywords.matched
        low = text.lower()
        unsupported = [s for s in matched if not is_grounded(s, low)]
        alias = [s for s in matched if not is_literally_present(s, low)]
        out["unsupported_matches"] += len(unsupported)
        out["case_rows"].append([case_id, match.overall_score, ref.overall_score, f"{lo}-{hi}",
                                 "PASS" if in_band else "FAIL", ", ".join(unsupported) or "-",
                                 ", ".join(alias) or "-"])

        if not args.no_report:
            print(f"Generating report: {case_id}")
            report = call(generate_report, text, jds[jid], match)
            if report is None:
                out["failed_calls"] += 1
                continue
            out["reports_done"] += 1
            false_gaps = [g.skill for g in report.gaps if is_literally_present(g.skill, low)]
            out["false_gaps"] += len(false_gaps)
            support = [evidence_support(s.evidence, low) for s in report.strengths]
            out["evidence"] += support
            allowed = set(NUMBER.findall(text)) | set(NUMBER.findall(JDS[jid]["text"])) \
                | set(NUMBER.findall(match.model_dump_json()))
            numbers = set(NUMBER.findall(report_text(report)))
            unverified = sorted(numbers - allowed)
            out["unverified_numbers"] += len(unverified)
            out["report_rows"].append([case_id, len(report.strengths), pct(avg(support)) if support else "-",
                                       ", ".join(false_gaps) or "-", ", ".join(unverified) or "-"])

    for better, worse in PAIRS:
        if better in scores and worse in scores:
            ok = scores[better] > scores[worse]
            out["pairs_ok"] += ok
            out["pair_rows"].append([better, scores[better], worse, scores[worse], "PASS" if ok else "FAIL"])
    return out


def evidence_support(evidence: str, text_lower: str) -> float:
    """Share of the evidence's words that really appear in the resume (1.0 = fully grounded)."""
    words = re.findall(r"[a-z0-9+#]{4,}", evidence.lower())
    return sum(w in text_lower for w in words) / len(words) if words else 1.0


def report_text(report) -> str:
    parts = [report.summary]
    parts += [f"{s.title} {s.evidence}" for s in report.strengths]
    parts += [g.suggestion for g in report.gaps]
    parts += [t.tip for t in report.resume_tips]
    return " ".join(parts)


# ---------- report ----------

def build_report(guard: dict, llm: dict | None, model: str) -> str:
    L = [f"# Accuracy report\n\nGenerated {datetime.now():%Y-%m-%d %H:%M} | model: {model} | "
         f"{len(RESUMES)} resumes x {len(JDS)} job descriptions, {len(CASES)} match cases (all synthetic)\n"]
    head = [["Guardrail checks passed", f"{guard['passed']}/{guard['total']}", "all"]]
    if llm:
        n = llm["cases_done"]
        head += [
            ["Resume skills: recall (found what is there)", pct(avg(llm["resume_recall"])), ">= 90%"],
            ["Resume skills: precision (no extras)", pct(avg(llm["resume_precision"])), ">= 85%"],
            ["Skills invented (not in resume text)", llm["invented_skills"], "0"],
            ["Experience years: average error", f"{avg(llm['year_errors']):.2f} yrs", "<= 0.3"],
            ["JD required skills: recall", pct(avg(llm["jd_required_recall"])), ">= 90%"],
            ["JD required skills: precision", pct(avg(llm["jd_required_precision"])), ">= 90%"],
            ["Scores inside the expected range", f"{llm['in_band']}/{n}", "all"],
            ["Better match scores higher (pairs)", f"{llm['pairs_ok']}/{len(llm['pair_rows'])}", "all"],
            ["Matched skills not in resume text", llm["unsupported_matches"], "0"],
        ]
        if llm["reports_done"]:
            head += [
                ["Report evidence found in resume", pct(avg(llm["evidence"])), ">= 85%"],
                ["Gaps that are actually in the resume", llm["false_gaps"], "0"],
                ["Numbers in report not in resume/JD/score", llm["unverified_numbers"], "0"],
            ]
        if llm["failed_calls"]:
            head.append(["Gemini calls that failed (rerun later)", llm["failed_calls"], "0"])
    L += ["## Summary\n", md_table(["Metric", "Result", "Target"], head), "\n"]
    L += ["## Guardrails\n", md_table(["Case", "Expected", "Got", ""], guard["rows"]), "\n"]
    if llm:
        L += ["## Resume extraction\n", md_table(
            ["Resume", "Precision", "Recall", "F1", "Years (true / found)", "Missed", "Extra", "Invented"],
            llm["resume_rows"]), "\n"]
        L += ["## Job description extraction\n", md_table(
            ["JD", "Required precision", "Required recall", "Preferred recall", "Required missed"],
            llm["jd_rows"]), "\n"]
        L += ["## Match scores\n", "Reference = score with perfect skill extraction (no JD keywords), "
              "so the gap to Score shows how much extraction errors move the result. 'Alias matches' are "
              "skills matched through a related name (for example MySQL for SQL).\n",
              md_table(["Case", "Score", "Reference", "Expected range", "", "Unsupported", "Alias matches"],
                       llm["case_rows"]), "\n"]
        L += [md_table(["Better match", "Score", "Worse match", "Score", ""], llm["pair_rows"]), "\n"]
        if llm["report_rows"]:
            L += ["## Report faithfulness\n", md_table(
                ["Case", "Strengths", "Evidence grounded", "False gaps", "Unverified numbers"],
                llm["report_rows"]), "\n"]
    return "\n".join(L)


def main(argv=None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true", help="guardrail checks only")
    parser.add_argument("--no-report", action="store_true", help="skip report generation calls")
    parser.add_argument("--pause", type=float, default=6.0, help="seconds between Gemini calls")
    args = parser.parse_args(argv)

    try:
        from app.core.config import get_settings
        model = get_settings().model_name
    except Exception:
        model = "n/a"

    print("Running guardrail checks...")
    guard = run_guardrails()
    llm = None if args.offline else run_llm_parts(args)
    text = build_report(guard, llm, model)
    REPORT_PATH.write_text(text, encoding="utf-8")
    print("\n" + text)
    print(f"\nSaved to {REPORT_PATH}")


if __name__ == "__main__":
    main()