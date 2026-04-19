import { useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { Sidebar } from '../components/Sidebar'
import { Breadcrumb } from '../components/Breadcrumb'
import type { Agent } from '../types/agent'

type DashboardPageProps = {
  userEmail: string
  agents: Agent[]
  onLogout: () => void
}

const ITEMS_PER_PAGE = 6

export function DashboardPage({
  userEmail,
  agents,
  onLogout,
}: DashboardPageProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<'all' | 'connected' | 'disconnected'>('all')
  const [currentPage, setCurrentPage] = useState(1)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [copiedAgentId, setCopiedAgentId] = useState<string | null>(null)

  const linkedTokens = agents.filter((agent) => Boolean(agent.botToken)).length

  const handleCopyName = (name: string, agentId: string) => {
    navigator.clipboard.writeText(name)
    setCopiedAgentId(agentId)
    setTimeout(() => setCopiedAgentId(null), 2000)
  }

  const handleCopyToken = (token: string, agentId: string) => {
    navigator.clipboard.writeText(token)
    setCopiedAgentId(agentId)
    setTimeout(() => setCopiedAgentId(null), 2000)
  }

  // Filter and search agents
  const filteredAgents = useMemo(() => {
    return agents.filter((agent) => {
      const matchesSearch =
        agent.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        agent.botUsername.toLowerCase().includes(searchQuery.toLowerCase()) ||
        agent.role.toLowerCase().includes(searchQuery.toLowerCase())

      if (statusFilter === 'all') {
        return matchesSearch
      }

      const connectionStatus = agent.telegramConnectionStatus || 'disconnected'
      return matchesSearch && connectionStatus === statusFilter
    })
  }, [agents, searchQuery, statusFilter])

  // Pagination
  const totalPages = Math.ceil(filteredAgents.length / ITEMS_PER_PAGE)
  const paginatedAgents = useMemo(() => {
    const startIndex = (currentPage - 1) * ITEMS_PER_PAGE
    return filteredAgents.slice(startIndex, startIndex + ITEMS_PER_PAGE)
  }, [filteredAgents, currentPage])

  const handlePreviousPage = () => {
    setCurrentPage((prev) => Math.max(1, prev - 1))
  }

  const handleNextPage = () => {
    setCurrentPage((prev) => Math.min(totalPages, prev + 1))
  }

  const toggleMobileMenu = () => {
    setSidebarOpen(!sidebarOpen)
  }

  return (
    <div className="dashboard-layout">
      <Sidebar
        userEmail={userEmail}
        onLogout={onLogout}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <main className="dashboard-main">
        <Breadcrumb />

        <div className="page-bg">
          <div className="page-shell dashboard-shell">
            {/* Mobile menu toggle */}
            <button
              className="mobile-menu-toggle"
              onClick={toggleMobileMenu}
              aria-label="Toggle menu"
            >
              ☰
            </button>

            {/* Header */}
            <header className="dashboard-header card">
              <div>
                <p className="eyebrow dark-eyebrow">Control Center</p>
                <h1>Your agents</h1>
                <p className="subtle">Logged in as {userEmail}</p>
              </div>

              <Link to="/agents/new" className="btn btn-primary">
                Create New Agent
              </Link>
            </header>

            {/* Stats */}
            <section className="stats-strip" aria-label="dashboard-metrics">
              <article className="card stat-card">
                <p>Total agents</p>
                <strong>{agents.length}</strong>
              </article>
              <article className="card stat-card">
                <p>Tokens linked</p>
                <strong>{linkedTokens}</strong>
              </article>
              <article className="card stat-card">
                <p>Connected</p>
                <strong>
                  {agents.filter((a) => a.telegramConnectionStatus === 'connected').length}
                </strong>
              </article>
              <article className="card stat-card">
                <p>Messages sent</p>
                <strong>{agents.reduce((sum, a) => sum + (a.messagesSent || 0), 0)}</strong>
              </article>
            </section>

            {/* Search & Filter */}
            <section className="card filter-section">
              <div className="filter-controls">
                <div className="search-box">
                  <input
                    type="text"
                    placeholder="Search by name, username, or role..."
                    value={searchQuery}
                    onChange={(e) => {
                      setSearchQuery(e.target.value)
                      setCurrentPage(1)
                    }}
                    className="form-input"
                  />
                  {searchQuery && (
                    <button
                      className="search-clear"
                      onClick={() => {
                        setSearchQuery('')
                        setCurrentPage(1)
                      }}
                    >
                      ✕
                    </button>
                  )}
                </div>

                <select
                  value={statusFilter}
                  onChange={(e) => {
                    setStatusFilter(e.target.value as typeof statusFilter)
                    setCurrentPage(1)
                  }}
                  className="form-select"
                >
                  <option value="all">All Status</option>
                  <option value="connected">Connected</option>
                  <option value="disconnected">Disconnected</option>
                </select>
              </div>
              {filteredAgents.length > 0 && (
                <p className="filter-info">
                  Showing {paginatedAgents.length} of {filteredAgents.length} agents
                </p>
              )}
            </section>

            {/* Agents List */}
            <section className="card agents-card">
              <h2>Available agents</h2>
              {filteredAgents.length === 0 ? (
                <div className="empty-state">
                  <p className="subtle">
                    {agents.length === 0
                      ? 'No agents yet. Click Create New Agent to launch your first one.'
                      : 'No agents match your search. Try adjusting your filters.'}
                  </p>
                  {agents.length === 0 && (
                    <Link to="/agents/new" className="btn btn-primary">
                      Create New Agent
                    </Link>
                  )}
                </div>
              ) : (
                <>
                  <ul className="agent-grid">
                    {paginatedAgents.map((agent) => (
                      <li key={agent.id} className="agent-item">
                        <div className="agent-chip">@{agent.botUsername || 'pending'}</div>
                        <h3>{agent.name}</h3>
                        <p className="agent-role">{agent.role}</p>
                        <div className="agent-status">
                          <p className="subtle">Bot ID: {agent.botId || 'missing'}</p>
                          <p className="subtle">
                            Bot token: {agent.botToken ? '✓ Linked' : '✕ Not linked'}
                          </p>
                          <p className="subtle">
                            Sent to endpoint: {agent.deliveryStatus === 'sent' ? '✓ Yes' : '✕ No'}
                          </p>
                        </div>

                        {/* Copy Options */}
                        <div className="agent-copy-options">
                          <button
                            className="copy-btn"
                            onClick={() => handleCopyName(agent.name, agent.id)}
                            title="Copy agent name"
                          >
                            {copiedAgentId === agent.id ? '✓ Copied' : 'Copy Name'}
                          </button>
                          {agent.botToken && (
                            <button
                              className="copy-btn"
                              onClick={() => handleCopyToken(agent.botToken, agent.id)}
                              title="Copy bot token"
                            >
                              {copiedAgentId === agent.id ? '✓ Copied' : 'Copy Token'}
                            </button>
                          )}
                        </div>
                      </li>
                    ))}
                  </ul>

                  {/* Pagination */}
                  {totalPages > 1 && (
                    <div className="pagination">
                      <button
                        className="btn btn-ghost"
                        onClick={handlePreviousPage}
                        disabled={currentPage === 1}
                      >
                        ← Previous
                      </button>
                      <div className="pagination-info">
                        Page {currentPage} of {totalPages}
                      </div>
                      <button
                        className="btn btn-ghost"
                        onClick={handleNextPage}
                        disabled={currentPage === totalPages}
                      >
                        Next →
                      </button>
                    </div>
                  )}
                </>
              )}
            </section>

            {/* Quick Actions */}
            <section className="quick-actions" aria-label="dashboard-quick-actions">
              <article className="card action-card">
                <h3>Need another bot?</h3>
                <p className="subtle">Create a new agent and upload token from BotFather.</p>
                <Link to="/agents/new" className="btn btn-primary">
                  Start New Agent
                </Link>
              </article>
              <article className="card action-card">
                <h3>Review your flow</h3>
                <p className="subtle">Return to landing to review onboarding and process guide.</p>
                <Link to="/" className="btn btn-ghost">
                  Go to Landing
                </Link>
              </article>
            </section>
          </div>
        </div>
      </main>
    </div>
  )
}
