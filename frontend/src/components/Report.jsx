const IMPORTANCE = { required: "Required", preferred: "Preferred", keyword: "Keyword" };

export default function Report({ report, error }) {
  if (!report) {
    return (
      <section className="panel">
        <h2>Detailed report</h2>
        <p className="notice">
          {error || "The detailed report is not available right now."} Your score above is still
          valid. Run the check again in a minute to get the report.
        </p>
      </section>
    );
  }

  return (
    <>
      <section className="panel" aria-labelledby="summary-heading">
        <h2 id="summary-heading">Summary</h2>
        <p className="summary">{report.summary}</p>
      </section>

      {report.strengths.length > 0 && (
        <section className="panel" aria-labelledby="strengths-heading">
          <h2 id="strengths-heading">What works in your favour</h2>
          <ul className="items">
            {report.strengths.map((s) => (
              <li key={s.title}>
                <h3>{s.title}</h3>
                <blockquote>{s.evidence}</blockquote>
              </li>
            ))}
          </ul>
        </section>
      )}

      {report.gaps.length > 0 && (
        <section className="panel" aria-labelledby="gaps-heading">
          <h2 id="gaps-heading">What to work on</h2>
          <ul className="items">
            {report.gaps.map((g) => (
              <li key={g.skill}>
                <h3>
                  {g.skill} <span className={`tag tag-${g.importance}`}>{IMPORTANCE[g.importance]}</span>
                </h3>
                <p>{g.suggestion}</p>
              </li>
            ))}
          </ul>
        </section>
      )}

      {report.resume_tips.length > 0 && (
        <section className="panel" aria-labelledby="tips-heading">
          <h2 id="tips-heading">Resume tips</h2>
          <ul className="items">
            {report.resume_tips.map((t) => (
              <li key={t.section + t.tip}>
                <h3>{t.section}</h3>
                <p>{t.tip}</p>
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  );
}