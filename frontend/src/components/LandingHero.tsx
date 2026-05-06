interface LandingHeroProps {
  onStart: () => void;
}

function LandingHero({ onStart }: LandingHeroProps) {
  return (
    <section className="landing-hero">
      <div className="hero-pattern" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
      <div className="brand-lockup" aria-label="Gies College of Business and University of Illinois Urbana-Champaign">
        <div className="block-i-mark" aria-hidden="true">
          <img src="https://cdn.brand.illinois.edu/touch-icon-180x180.png" alt="" />
        </div>
        <div>
          <strong>Gies College of Business</strong>
          <span>University of Illinois Urbana-Champaign</span>
        </div>
      </div>
      <div className="hero-content">
        <p className="eyebrow">Innovation & Transformation Prototype</p>
        <h1>Rubric-aware feedback before final submission</h1>
        <p className="intro-copy">
          Paste a draft and rubric. Get formative revision guidance that stays grounded in the student’s work and the
          assignment criteria.
        </p>
        <button type="button" className="hero-cta" onClick={onStart}>
          Start revision pass
        </button>
      </div>
    </section>
  );
}

export default LandingHero;
