import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { getFirebaseWriteErrorMessage, saveAgentToFirebase } from '../lib/firebase'
import type { Agent } from '../types/agent'

type CreateAgentPageProps = {
  userId: string
  userEmail: string
  onCreateAgent: (agent: Agent) => void
}

export function CreateAgentPage({
  userId,
  userEmail,
  onCreateAgent,
}: CreateAgentPageProps) {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [botToken, setBotToken] = useState('')
  const [status, setStatus] = useState<'idle' | 'saving' | 'error' | 'success'>('idle')
  const [message, setMessage] = useState('')

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    const trimmedName = name.trim()
    const trimmedToken = botToken.trim()

    if (!trimmedName || !trimmedToken.includes(':')) {
      setStatus('error')
      setMessage('Add an agent name and a valid bot token from BotFather.')
      return
    }

    const botId = trimmedToken.split(':')[0] ?? ''
    if (!botId) {
      setStatus('error')
      setMessage('Could not read bot ID from token. Use a valid BotFather token.')
      return
    }

    const nextAgent: Agent = {
      id: crypto.randomUUID(),
      name: trimmedName,
      role: 'General assistant',
      botId,
      botUsername: '',
      botToken: trimmedToken,
      deliveryStatus: 'sent',
    }

    setStatus('saving')
    setMessage('Saving agent token to Firebase...')

    void (async () => {
      try {
        try {
          const firebaseSaved = await saveAgentToFirebase({
            userId,
            userEmail,
            agent: nextAgent,
          })

          if (!firebaseSaved) {
            setStatus('error')
            setMessage('Firebase is not configured. Check Firebase env values.')
            return
          } else {
            setMessage('Agent token uploaded to Firebase successfully.')
          }
        } catch (error) {
          setStatus('error')
          setMessage(getFirebaseWriteErrorMessage(error))
          return
        }

        onCreateAgent(nextAgent)
        setStatus('success')
        navigate('/dashboard')
      } catch (error) {
        setStatus('error')
        setMessage(
          error instanceof Error ? error.message : 'Could not save agent.',
        )
      }
    })()
  }

  return (
    <div className="page-bg">
      <div className="page-shell create-shell">
        <div className="back-container">
          <button
            className="btn btn-ghost back-button"
            type="button"
            onClick={() => navigate(-1)}
          >
            ← Back
          </button>
        </div>

        <div className="form-container">
          <section className="hero-panel">
            <div>
              <p className="eyebrow">Telegram manual flow</p>
              <h1>Create in Telegram, then upload token here.</h1>
              <p className="hero-copy">
                You create the bot yourself in BotFather. This page only captures the token
                and uploads bot ID and token into Firebase for your account.
              </p>
            </div>

            <div className="flow-card">
              <h2>What happens next</h2>
              <ol>
                <li>Open BotFather and run /newbot.</li>
                <li>Copy the token BotFather gives you.</li>
                <li>Paste token here and save to Firebase.</li>
              </ol>
            </div>

            <div className="glass-note">
              <strong>Pro tip</strong>
              <p>
                Use a clean naming convention like team-purpose-version so dashboard search
                stays organized as your agents grow.
              </p>
            </div>
          </section>

          <section className="card auth-card">
          <p className="eyebrow dark-eyebrow">Create Agent</p>
          <h1>New bot setup</h1>
          <p className="subtle">
            Logged in as {userEmail}. After save, token and bot ID will be written to
            Firebase under your user account.
          </p>

          <div className="cta-row">
            <button className="btn btn-telegram" type="button" onClick={() => window.open('https://t.me/BotFather', '_blank', 'noopener,noreferrer')}>
              Open BotFather on Telegram
            </button>
          </div>

          <form className="form-stack" onSubmit={handleSubmit}>
            <label>
              Agent name
              <input
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="Support Wingman"
              />
            </label>

            <label>
              Telegram bot token
              <input
                value={botToken}
                onChange={(event) => setBotToken(event.target.value)}
                placeholder="123456789:AA..."
              />
            </label>

            <button className="btn btn-primary" type="submit" disabled={status === 'saving'}>
              {status === 'saving' ? 'Saving...' : 'Save Agent'}
            </button>

            <button
              className="btn btn-ghost"
              type="button"
              onClick={() => {
                setName('')
                setBotToken('')
                setMessage('')
                setStatus('idle')
              }}
            >
              Clear form
            </button>
          </form>

          {message && (
            <p
              className={
                status === 'error' ? 'status status-error' : 'status status-success'
              }
            >
              {message}
            </p>
          )}
        </section>
        </div>
      </div>
    </div>
  )
}
