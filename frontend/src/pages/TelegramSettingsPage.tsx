import type { FormEvent } from 'react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { TelegramUserConfig } from '../types/telegramConfig'

type TelegramSettingsPageProps = {
  userEmail: string
  initialConfig: TelegramUserConfig
  onSaveConfig: (config: TelegramUserConfig) => void
}

export function TelegramSettingsPage({
  userEmail,
  initialConfig,
  onSaveConfig,
}: TelegramSettingsPageProps) {
  const navigate = useNavigate()
  const [apiId, setApiId] = useState(initialConfig.apiId)
  const [apiHash, setApiHash] = useState(initialConfig.apiHash)
  const [appTitle, setAppTitle] = useState(initialConfig.appTitle)
  const [shortName, setShortName] = useState(initialConfig.shortName)
  const [registrationEndpoint, setRegistrationEndpoint] = useState(
    initialConfig.registrationEndpoint,
  )
  const [sessionString, setSessionString] = useState(initialConfig.sessionString)
  const [status, setStatus] = useState<'idle' | 'error'>('idle')

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    if (!apiId.trim() || !apiHash.trim()) {
      setStatus('error')
      return
    }

    onSaveConfig({
      apiId: apiId.trim(),
      apiHash: apiHash.trim(),
      appTitle: appTitle.trim(),
      shortName: shortName.trim(),
      registrationEndpoint: registrationEndpoint.trim(),
      sessionString: sessionString.trim(),
    })

    navigate('/dashboard')
  }

  return (
    <div className="page-bg">
      <div className="page-shell single-col-shell">
        <section className="card auth-card">
          <p className="eyebrow dark-eyebrow">Telegram User Settings</p>
          <h1>Save your own API keys</h1>
          <p className="subtle">
            Logged in as {userEmail}. These values are saved only for this user in
            this browser.
          </p>

          <form className="form-stack" onSubmit={handleSubmit}>
            <label>
              Telegram API ID
              <input
                value={apiId}
                onChange={(event) => setApiId(event.target.value)}
                placeholder="31664157"
              />
            </label>

            <label>
              Telegram API Hash
              <input
                value={apiHash}
                onChange={(event) => setApiHash(event.target.value)}
                placeholder="a5bd..."
              />
            </label>

            <label>
              App title
              <input
                value={appTitle}
                onChange={(event) => setAppTitle(event.target.value)}
                placeholder="HIVEMIND"
              />
            </label>

            <label>
              Short name
              <input
                value={shortName}
                onChange={(event) => setShortName(event.target.value)}
                placeholder="HIVMD"
              />
            </label>

            <label>
              Registration endpoint (optional)
              <input
                value={registrationEndpoint}
                onChange={(event) => setRegistrationEndpoint(event.target.value)}
                placeholder="https://your-backend.com/api/telegram/register-bot"
              />
            </label>

            <label>
              Telegram session string
              <input
                type="password"
                value={sessionString}
                onChange={(event) => setSessionString(event.target.value)}
                placeholder="Paste your Telegram StringSession here"
              />
            </label>

            <button className="btn btn-primary" type="submit">
              Save Settings
            </button>
          </form>

          {status === 'error' && (
            <p className="status status-error">
              Telegram API ID, API Hash, and session string are required.
            </p>
          )}
        </section>
      </div>
    </div>
  )
}
