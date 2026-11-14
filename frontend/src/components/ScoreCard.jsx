// The fit meter is the main visual: a ruler from 0 to 100 with a marker at the score.
const TICKS = Array.from({ length: 21 }, (_, i) => i * 5);

function BreakdownRow({ label, value }) {
  const known = value !== null && value !== undefined;
  return (
    <div className="breakdown-row">
      <span className="breakdown-label">{label}</span>
      <div className="bar" aria-hidden="true">
        <div className="bar-fill" style={{ width: known ? `${Math.min(100, value)}%` : "0%" }} />
      </div>
      <span className="breakdown-value">{known ? `${Math.round(value)}%` : "Not in this job"}</span>
    </div>
  );
}

export default function ScoreCard({ match }) {
  const { overall_score: score, label, breakdown } = match;
  const years = match.candidate_experience_years;
  const needed = match.required_experience_years;

  return (
    <section className="score" aria-labelledby="score-heading">
      <h2 id="score-heading" className="visually-hidden">Match score</h2>
      <div className="score-top">
        <p className="score-number" aria-label={`Match score ${score} out of 100`}>
          {score}<span className="score-max">/100</span>
        </p>
        <p className="score-label">{label}</p>
      </div>

      <div className="meter" role="img" aria-label={`Score ${score} on a scale of 0 to 100`}>
        <div className="meter-fill" style={{ width: `${score}%` }} />
        <div className="meter-ticks">
          {TICKS.map((t) => (
            <span key={t} className={`tick${t % 25 === 0 ? " tick-major" : ""}`} />
          ))}
        </div>
        <div className="meter-marker" style={{ left: `${score}%` }} />
        <div className="meter-scale"><span>0</span><span>25</span><span>50</span><span>75</span><span>100</span></div>
      </div>

      <div className="breakdown">
        <BreakdownRow label="Required skills" value={breakdown.required_skills} />
        <BreakdownRow label="Preferred skills" value={breakdown.preferred_skills} />
        <BreakdownRow label="Keywords" value={breakdown.keywords} />
        <BreakdownRow label="Experience" value={breakdown.experience} />
      </div>
      <p className="hint">
        Your resume shows {years} {years === 1 ? "year" : "years"} of experience
        {needed ? `; the job asks for ${needed}.` : "; the job does not ask for a minimum."}
      </p>
    </section>
  );
}