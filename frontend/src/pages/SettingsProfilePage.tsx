import { useState } from 'react'
import { Sidebar } from '../components/Sidebar'
import { Breadcrumb } from '../components/Breadcrumb'

type SettingsProfilePageProps = {
  userEmail: string
  onLogout: () => void
}

export function SettingsProfilePage({ userEmail, onLogout }: SettingsProfilePageProps) {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [formData, setFormData] = useState({
    name: userEmail.split('@')[0],
    timezone: 'UTC',
    notificationsEnabled: true,
  })
  const [isSaving, setIsSaving] = useState(false)
  const [saveMessage, setSaveMessage] = useState('')

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? (e.target as HTMLInputElement).checked : value,
    }))
  }

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSaving(true)
    setSaveMessage('')

    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1000))

    setIsSaving(false)
    setSaveMessage('Profile updated successfully!')
    setTimeout(() => setSaveMessage(''), 3000)
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
                <h1>Profile</h1>
                <p className="subtle">Manage your account information</p>
              </div>
            </header>

            <section className="card settings-section">
              <h2>Account Information</h2>
              <div className="profile-info">
                <div className="info-item">
                  <label>Email Address</label>
                  <p className="info-value">{userEmail}</p>
                </div>
              </div>
            </section>

            <section className="card settings-section">
              <h2>Profile Settings</h2>
              <form onSubmit={handleSaveProfile} className="settings-form">
                <div className="form-group">
                  <label htmlFor="name" className="form-label">
                    Display Name
                  </label>
                  <input
                    id="name"
                    name="name"
                    type="text"
                    value={formData.name}
                    onChange={handleInputChange}
                    className="form-input"
                    placeholder="Enter your name"
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="timezone" className="form-label">
                    Timezone
                  </label>
                  <select
                    id="timezone"
                    name="timezone"
                    value={formData.timezone}
                    onChange={handleInputChange}
                    className="form-select"
                  >
                    <option value="UTC">UTC</option>
                    <option value="EST">Eastern Time (EST)</option>
                    <option value="CST">Central Time (CST)</option>
                    <option value="MST">Mountain Time (MST)</option>
                    <option value="PST">Pacific Time (PST)</option>
                    <option value="GMT">GMT</option>
                    <option value="CET">Central European Time (CET)</option>
                    <option value="IST">India Standard Time (IST)</option>
                    <option value="JST">Japan Standard Time (JST)</option>
                  </select>
                </div>

                <div className="form-group checkbox-group">
                  <label htmlFor="notifications" className="checkbox-label">
                    <input
                      id="notifications"
                      name="notificationsEnabled"
                      type="checkbox"
                      checked={formData.notificationsEnabled}
                      onChange={handleInputChange}
                    />
                    <span>Enable email notifications for bot activity</span>
                  </label>
                </div>

                <div className="form-actions">
                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={isSaving}
                  >
                    {isSaving ? 'Saving...' : 'Save Changes'}
                  </button>
                  {saveMessage && <p className="success-message">{saveMessage}</p>}
                </div>
              </form>
            </section>
          </div>
        </div>
      </main>
    </div>
  )
}
