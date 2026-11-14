// Matched skills get a highlighter mark, missing skills a dashed outline.
function Group({ title, coverage }) {
  const total = coverage.matched.length + coverage.missing.length;
  if (total === 0) return null;
  return (
    <div className="skill-group">
      <h3>
        {title} <span className="count">{coverage.matched.length} of {total} found</span>
      </h3>
      <ul className="chips">
        {coverage.matched.map((s) => (
          <li key={`m-${s}`} className="chip chip-matched"><span className="visually-hidden">Found: </span>{s}</li>
        ))}
        {coverage.missing.map((s) => (
          <li key={`x-${s}`} className="chip chip-missing"><span className="visually-hidden">Missing: </span>{s}</li>
        ))}
      </ul>
    </div>
  );
}

export default function SkillGroups({ match }) {
  return (
    <section className="panel" aria-labelledby="skills-heading">
      <h2 id="skills-heading">Skills the job asks for</h2>
      <p className="hint">Highlighted skills are on your resume. Dashed ones are not.</p>
      <Group title="Required" coverage={match.required} />
      <Group title="Preferred" coverage={match.preferred} />
      <Group title="Keywords" coverage={match.keywords} />
    </section>
  );
}