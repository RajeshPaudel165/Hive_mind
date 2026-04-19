import './Skeleton.css'

export function SkeletonText({ width = '100%', height = '1rem' }) {
  return <div className="skeleton skeleton-text" style={{ width, height }} />
}

export function SkeletonCard() {
  return (
    <div className="skeleton-card">
      <SkeletonText width="60%" height="1.2rem" />
      <SkeletonText width="100%" height="0.8rem" />
      <SkeletonText width="85%" height="0.8rem" />
      <SkeletonText width="70%" height="0.8rem" />
    </div>
  )
}

export function SkeletonAgentItem() {
  return (
    <div className="skeleton-agent-item">
      <SkeletonText width="140px" height="1.8rem" />
      <SkeletonText width="100%" height="0.9rem" />
      <SkeletonText width="95%" height="0.9rem" />
      <SkeletonText width="90%" height="0.9rem" />
    </div>
  )
}

export function SkeletonDashboard() {
  return (
    <div className="page-bg">
      <div className="page-shell dashboard-shell">
        <div className="dashboard-header card">
          <div>
            <SkeletonText width="120px" height="0.8rem" />
            <SkeletonText width="150px" height="1.8rem" />
          </div>
        </div>

        <section className="stats-strip" aria-label="dashboard-metrics">
          <article className="card stat-card">
            <SkeletonText width="100%" height="0.8rem" />
            <SkeletonText width="50px" height="1.5rem" />
          </article>
          <article className="card stat-card">
            <SkeletonText width="100%" height="0.8rem" />
            <SkeletonText width="50px" height="1.5rem" />
          </article>
          <article className="card stat-card">
            <SkeletonText width="100%" height="0.8rem" />
            <SkeletonText width="100px" height="1.5rem" />
          </article>
        </section>

        <section className="card agents-card">
          <SkeletonText width="120px" height="1.3rem" />
          <ul className="agent-grid">
            {Array(3)
              .fill(0)
              .map((_, i) => (
                <li key={i}>
                  <SkeletonAgentItem />
                </li>
              ))}
          </ul>
        </section>
      </div>
    </div>
  )
}
