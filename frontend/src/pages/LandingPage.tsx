import { Link } from 'react-router-dom'

export function LandingPage() {
  return (
    <div className="page-bg landing-page">
      <nav className="landing-nav">
        <div className="nav-left">
          <span className="logo">HiveMind</span>
        </div>
        <div className="nav-right">
          <Link to="/login" className="nav-link">
            Docs
          </Link>
          <Link to="/login" className="btn btn-primary nav-btn">
            Sign up →
          </Link>
        </div>
      </nav>

      <div className="landing-hero">
        <div className="hero-content">
          <p className="hero-badge">Telegram Bot Management</p>

          <h1 className="hero-headline">
            Create and manage Telegram agents from <span className="highlight">one dashboard</span>
          </h1>

          <p className="hero-description">
            Build bots, upload tokens, and track deployments. All in one focused place.
            No complexity. Built for speed.
          </p>

          <div className="hero-buttons">
            <Link to="/login" className="btn btn-primary btn-lg">
              Get Started →
            </Link>
            <Link to="/login" className="btn btn-outline btn-lg">
              Documentation
            </Link>
          </div>

          <div className="hero-command">
            <code>$ npm start hivemind</code>
          </div>
        </div>
      </div>

      <div className="landing-features">
        <article className="feature-item">
          <h3>⚡ Fast Setup</h3>
          <p>Login, create agent, paste token. Three steps to go live.</p>
        </article>
        <article className="feature-item">
          <h3>🔒 Secure Tokens</h3>
          <p>Firebase-backed storage. Your tokens stay encrypted and private.</p>
        </article>
        <article className="feature-item">
          <h3>📊 Full Control</h3>
          <p>Manual bot creation means you stay in command. No surprises.</p>
        </article>
      </div>
    </div>
  )
}
