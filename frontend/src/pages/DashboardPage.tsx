import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Sidebar } from '../components/Sidebar'
import { Breadcrumb } from '../components/Breadcrumb'
import {
  getAgentPermissions,
  getOpenClawHealth,
  getTelegramWorkerStatus,
  updateAgentPermission,
  type AgentPermissions,
  type OpenClawHealth,
  type TelegramWorkerStatus,
  type ToolPermissionState,
} from '../lib/hiveBackend'
import type { Agent } from '../types/agent'

type DashboardPageProps = {
  userEmail: string
  agents: Agent[]
  onLogout: () => void
  onDeleteAgent: (agent: Agent) => Promise<void>
}

const ITEMS_PER_PAGE = 6
const STATUS_REFRESH_MS = 5000
const TOOL_LABELS: Record<string, string> = {
  memory_read: 'Read memory',
  memory_write: 'Write memory',
  pulse: 'Pulse',
  openclaw_chat: 'OpenClaw chat',
  telegram_send: 'Telegram send',
  brave_search: 'Brave search',
  gmail: 'Gmail',
  calendar: 'Calendar',
  notion: 'Notion',
  todo: 'Todo',
  notes: 'Notes',
  filesystem: 'Filesystem',
  browser: 'Browser',
  shell: 'Shell',
}

export function DashboardPage({
  userEmail,
  agents,
  onLogout,
  onDeleteAgent,
}: DashboardPageProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<'all' | 'connected' | 'disconnected'>('all')
  const [currentPage, setCurrentPage] = useState(1)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [copiedAgentId, setCopiedAgentId] = useState<string | null>(null)
  const [deletingAgentId, setDeletingAgentId] = useState<string | null>(null)
  const [deleteError, setDeleteError] = useState('')
  const [openclawHealth, setOpenclawHealth] = useState<OpenClawHealth | null>(null)
  const [workerStatuses, setWorkerStatuses] = useState<
    Record<string, TelegramWorkerStatus>
  >({})
  const [permissionsByAgent, setPermissionsByAgent] = useState<
    Record<string, AgentPermissions>
  >({})
  const [statusError, setStatusError] = useState('')
  const [permissionError, setPermissionError] = useState('')
  const [savingPermission, setSavingPermission] = useState<string | null>(null)

  const linkedTokens = agents.filter((agent) => Boolean(agent.botToken)).length
  const connectedAgents = agents.filter((agent) => {
    const agentId = agent.hiveAgentId || agent.id
    const liveStatus = workerStatuses[agentId]
    return liveStatus ? liveStatus.running : agent.telegramConnectionStatus === 'connected'
  }).length

  useEffect(() => {
    let cancelled = false

    async function refreshStatuses() {
      try {
        const [nextOpenclawHealth, nextWorkerStatuses] = await Promise.all([
          getOpenClawHealth(),
          Promise.all(
            agents.map(async (agent) => {
              const agentId = agent.hiveAgentId || agent.id
              const status = await getTelegramWorkerStatus(agentId)
              return [agentId, status] as const
            }),
          ),
        ])

        if (cancelled) {
          return
        }

        setOpenclawHealth(nextOpenclawHealth)
        setWorkerStatuses(Object.fromEntries(nextWorkerStatuses))
        setStatusError('')
      } catch (error) {
        if (!cancelled) {
          setStatusError(
            error instanceof Error ? error.message : 'Could not refresh live status.',
          )
        }
      }
    }

    void refreshStatuses()
    const intervalId = window.setInterval(() => {
      void refreshStatuses()
    }, STATUS_REFRESH_MS)

    return () => {
      cancelled = true
      window.clearInterval(intervalId)
    }
  }, [agents])

  useEffect(() => {
    let cancelled = false

    async function refreshPermissions() {
      if (agents.length === 0) {
        setPermissionsByAgent({})
        return
      }

      try {
        const nextPermissions = await Promise.all(
          agents.map(async (agent) => {
            const agentId = agent.hiveAgentId || agent.id
            const permissions = await getAgentPermissions(agentId)
            return [agentId, permissions] as const
          }),
        )

        if (cancelled) {
          return
        }

        setPermissionsByAgent(Object.fromEntries(nextPermissions))
        setPermissionError('')
      } catch (error) {
        if (!cancelled) {
          setPermissionError(
            error instanceof Error ? error.message : 'Could not load permissions.',
          )
        }
      }
    }

    void refreshPermissions()

    return () => {
      cancelled = true
    }
  }, [agents])

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

  const handleCopyAgentId = (agentId: string) => {
    navigator.clipboard.writeText(agentId)
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

      const agentId = agent.hiveAgentId || agent.id
      const liveWorkerStatus = workerStatuses[agentId]
      const connectionStatus = liveWorkerStatus
        ? liveWorkerStatus.running ? 'connected' : 'disconnected'
        : agent.telegramConnectionStatus || 'disconnected'
      return matchesSearch && connectionStatus === statusFilter
    })
  }, [agents, searchQuery, statusFilter, workerStatuses])

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

  const handleDeleteAgent = async (agent: Agent) => {
    const confirmed = window.confirm(
      `Delete ${agent.name}? This will stop its Telegram worker and remove it from the dashboard.`,
    )
    if (!confirmed) {
      return
    }

    setDeleteError('')
    setDeletingAgentId(agent.id)
    try {
      await onDeleteAgent(agent)
    } catch (error) {
      setDeleteError(
        error instanceof Error ? error.message : 'Could not delete agent.',
      )
    } finally {
      setDeletingAgentId(null)
    }
  }

  const handlePermissionChange = async (
    agentId: string,
    toolName: string,
    nextState: ToolPermissionState,
  ) => {
    setPermissionError('')
    setSavingPermission(`${agentId}:${toolName}`)
    try {
      const nextPermissions = await updateAgentPermission(
        agentId,
        toolName,
        nextState,
      )
      setPermissionsByAgent((current) => ({
        ...current,
        [agentId]: nextPermissions,
      }))
    } catch (error) {
      setPermissionError(
        error instanceof Error ? error.message : 'Could not update permission.',
      )
    } finally {
      setSavingPermission(null)
    }
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
                  {connectedAgents}
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
              {deleteError && <p className="status status-error">{deleteError}</p>}
              {statusError && <p className="status status-error">{statusError}</p>}
              {permissionError && <p className="status status-error">{permissionError}</p>}
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
                    {paginatedAgents.map((agent) => {
                      const agentId = agent.hiveAgentId || agent.id
                      const workerStatus = workerStatuses[agentId]
                      const workerRunning =
                        workerStatus?.running ??
                        agent.telegramConnectionStatus === 'connected'
                      const workerPid = workerStatus?.pid ?? agent.workerPid
                      const openclawReachable =
                        openclawHealth?.reachable ?? agent.openclawReachable
                      const permissions = permissionsByAgent[agentId]

                      return (
                      <li key={agent.id} className="agent-item">
                        <div className="agent-chip">@{agent.botUsername || 'pending'}</div>
                        <h3>{agent.name}</h3>
                        <p className="agent-role">{agent.role}</p>
                        <div className="agent-status">
                          <p className="subtle">HIVE ID: {agentId}</p>
                          <p className="subtle">
                            Runtime: {agent.runtimeProvider || 'local'}
                            {agent.runtimeMachineId ? ` / ${agent.runtimeMachineId}` : ''}
                          </p>
                          <p className="subtle">Bot ID: {agent.botId || 'missing'}</p>
                          <p className="subtle">
                            Bot token: {agent.botToken ? '✓ Linked' : '✕ Not linked'}
                          </p>
                          <p className="subtle">
                            Sent to endpoint: {agent.deliveryStatus === 'sent' ? '✓ Yes' : '✕ No'}
                          </p>
                          <p className="subtle">
                            OpenClaw: {openclawReachable ? '✓ Reachable' : '✕ Not ready'}
                          </p>
                          <p className="subtle">
                            Telegram worker: {workerRunning && workerPid ? `✓ PID ${workerPid}` : '✕ Not running'}
                          </p>
                        </div>

                        <details className="agent-permissions">
                          <summary>Tool permissions</summary>
                          {permissions ? (
                            <div className="permission-grid">
                              {permissions.available_tools.map((toolName) => {
                                const savingKey = `${agentId}:${toolName}`
                                return (
                                  <label className="permission-row" key={toolName}>
                                    <span>{TOOL_LABELS[toolName] || toolName}</span>
                                    <select
                                      value={permissions.tool_permissions[toolName]}
                                      disabled={savingPermission === savingKey}
                                      onChange={(event) => {
                                        void handlePermissionChange(
                                          agentId,
                                          toolName,
                                          event.target.value as ToolPermissionState,
                                        )
                                      }}
                                    >
                                      {permissions.states.map((state) => (
                                        <option key={state} value={state}>
                                          {state}
                                        </option>
                                      ))}
                                    </select>
                                  </label>
                                )
                              })}
                            </div>
                          ) : (
                            <p className="subtle">Loading permissions...</p>
                          )}
                          <p className="subtle permission-help">
                            Telegram: /permission allow memory_read
                          </p>
                        </details>

                        {/* Copy Options */}
                        <div className="agent-copy-options">
                          <button
                            className="copy-btn"
                            onClick={() => handleCopyName(agent.name, agent.id)}
                            title="Copy agent name"
                          >
                            {copiedAgentId === agent.id ? '✓ Copied' : 'Copy Name'}
                          </button>
                          <button
                            className="copy-btn"
                            onClick={() => handleCopyAgentId(agent.hiveAgentId || agent.id)}
                            title="Copy HIVE agent ID"
                          >
                            {copiedAgentId === agent.id ? '✓ Copied' : 'Copy HIVE ID'}
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
                          <button
                            className="copy-btn"
                            onClick={() => void handleDeleteAgent(agent)}
                            disabled={deletingAgentId === agent.id}
                            title="Delete agent"
                          >
                            {deletingAgentId === agent.id ? 'Deleting...' : 'Delete'}
                          </button>
                        </div>
                      </li>
                      )
                    })}
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
