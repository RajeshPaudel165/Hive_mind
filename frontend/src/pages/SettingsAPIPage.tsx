import { useState } from 'react'
import { Sidebar } from '../components/Sidebar'
import { Breadcrumb } from '../components/Breadcrumb'

type SettingsAPIPageProps = {
  userEmail: string
  onLogout: () => void
}

type APIKey = {
  id: string
  name: string
  key: string
  createdAt: string
  lastUsed?: string
}

export function SettingsAPIPage({ userEmail, onLogout }: SettingsAPIPageProps) {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [apiKeys, setApiKeys] = useState<APIKey[]>([
    {
      id: '1',
      name: 'Production Key',
      key: 'hm_live_xxxxxxxxxxxxxxxxxxxxxxxx',
      createdAt: '2024-01-15',
      lastUsed: '2024-04-18',
    },
  ])
  const [showNewKeyForm, setShowNewKeyForm] = useState(false)
  const [newKeyName, setNewKeyName] = useState('')
  const [copiedKey, setCopiedKey] = useState<string | null>(null)

  const handleGenerateKey = (e: React.FormEvent) => {
    e.preventDefault()
    if (!newKeyName.trim()) return

    const newKey: APIKey = {
      id: Date.now().toString(),
      name: newKeyName,
      key: `hm_live_${Math.random().toString(36).substring(2, 26)}`,
      createdAt: new Date().toISOString().split('T')[0],
    }

    setApiKeys([...apiKeys, newKey])
    setNewKeyName('')
    setShowNewKeyForm(false)
  }

  const handleDeleteKey = (id: string) => {
    if (window.confirm('Are you sure you want to delete this API key?')) {
      setApiKeys(apiKeys.filter((key) => key.id !== id))
    }
  }

  const handleCopyKey = (key: string) => {
    navigator.clipboard.writeText(key)
    setCopiedKey(key)
    setTimeout(() => setCopiedKey(null), 2000)
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
            <button
              className="mobile-menu-toggle"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              aria-label="Toggle menu"
            >
              ☰
            </button>

            <header className="dashboard-header card">
              <div>
                <p className="eyebrow dark-eyebrow">Settings</p>
                <h1>API Keys</h1>
                <p className="subtle">Manage your API credentials for programmatic access</p>
              </div>

              <button
                className="btn btn-primary"
                onClick={() => setShowNewKeyForm(!showNewKeyForm)}
              >
                {showNewKeyForm ? 'Cancel' : 'Generate New Key'}
              </button>
            </header>

            {showNewKeyForm && (
              <section className="card settings-section">
                <h2>Generate New API Key</h2>
                <form onSubmit={handleGenerateKey} className="settings-form">
                  <div className="form-group">
                    <label htmlFor="keyName" className="form-label">
                      Key Name
                    </label>
                    <input
                      id="keyName"
                      type="text"
                      value={newKeyName}
                      onChange={(e) => setNewKeyName(e.target.value)}
                      className="form-input"
                      placeholder="e.g., Production Key, Development Key"
                      required
                    />
                  </div>

                  <div className="form-actions">
                    <button type="submit" className="btn btn-primary">
                      Generate Key
                    </button>
                  </div>
                </form>
              </section>
            )}

            <section className="card settings-section">
              <h2>Your API Keys</h2>

              {apiKeys.length === 0 ? (
                <p className="subtle">
                  No API keys yet. Generate one to get started with programmatic access.
                </p>
              ) : (
                <div className="api-keys-list">
                  {apiKeys.map((apiKey) => (
                    <div key={apiKey.id} className="api-key-item">
                      <div className="key-info">
                        <h3>{apiKey.name}</h3>
                        <p className="subtle">
                          Created: {new Date(apiKey.createdAt).toLocaleDateString()}
                        </p>
                        {apiKey.lastUsed && (
                          <p className="subtle">
                            Last used: {new Date(apiKey.lastUsed).toLocaleDateString()}
                          </p>
                        )}
                      </div>

                      <div className="key-display">
                        <code className="key-value">{apiKey.key}</code>
                        <button
                          className="btn btn-ghost btn-sm"
                          onClick={() => handleCopyKey(apiKey.key)}
                        >
                          {copiedKey === apiKey.key ? '✓ Copied' : 'Copy'}
                        </button>
                      </div>

                      <button
                        className="btn btn-danger btn-sm"
                        onClick={() => handleDeleteKey(apiKey.id)}
                      >
                        Delete
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </section>

            <section className="card settings-section">
              <h2>API Documentation</h2>
              <p className="subtle">
                Learn how to use HiveMind API with our comprehensive documentation.
              </p>
              <a href="#" className="btn btn-ghost">
                View Documentation
              </a>
            </section>
          </div>
        </div>
      </main>
    </div>
  )
}
