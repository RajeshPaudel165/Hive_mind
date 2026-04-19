import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { getFirebaseAuthErrorMessage } from '../lib/firebase'

type LoginPageProps = {
  onLogin: (email: string, password: string) => Promise<void>
  onCreateAccount: (email: string, password: string) => Promise<void>
}

export function LoginPage({ onLogin, onCreateAccount }: LoginPageProps) {
  const navigate = useNavigate()
  const location = useLocation()
  const redirectPath =
    (location.state as { from?: string } | null)?.from ?? '/dashboard'

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [mode, setMode] = useState<'login' | 'register'>('register')
  const [status, setStatus] = useState<'idle' | 'submitting' | 'error'>('idle')
  const [errorMessage, setErrorMessage] = useState('')

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    if (!email.trim() || !password.trim()) {
      setStatus('error')
      setErrorMessage('Enter both email and password to continue.')
      return
    }

    setStatus('submitting')
    setErrorMessage('')

    void (async () => {
      try {
        if (mode === 'login') {
          await onLogin(email.trim(), password)
        } else {
          await onCreateAccount(email.trim(), password)
        }

        navigate(redirectPath, { replace: true })
      } catch (error) {
        setStatus('error')
        setErrorMessage(getFirebaseAuthErrorMessage(error))
      }
    })()
  }

  return (
    <div className="auth-page">
      <div className="auth-container">
        <div className="auth-form-section">
          <Link to="/" className="auth-logo-link">
            <div className="auth-logo">HiveMind</div>
          </Link>

          <div className="auth-content">
            <h1 className="auth-title">
              {mode === 'login' ? 'Welcome back' : 'Create an account'}
            </h1>
            <p className="auth-subtitle">
              {mode === 'login'
                ? 'Sign in to manage your Telegram agents'
                : 'Sign up and start managing Telegram agents'}
            </p>

            <form className="auth-form" onSubmit={handleSubmit}>
              <label className="form-label">
                <span>Email</span>
                <input
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="you@company.com"
                  className="form-input"
                />
              </label>

              <label className="form-label">
                <span>Password</span>
                <input
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="••••••••••••••••"
                  className="form-input"
                />
              </label>

              <button
                className="btn-submit"
                type="submit"
                disabled={status === 'submitting'}
              >
                {status === 'submitting'
                  ? 'Please wait...'
                  : mode === 'login'
                    ? 'Sign in'
                    : 'Create account'}
              </button>
            </form>

            {status === 'error' && (
              <div className="auth-error">{errorMessage}</div>
            )}

            <div className="auth-footer">
              {mode === 'login' ? (
                <>
                  <span>Don't have an account?</span>
                  <button
                    type="button"
                    className="link-btn"
                    onClick={() => {
                      setMode('register')
                      setErrorMessage('')
                    }}
                  >
                    Sign up
                  </button>
                </>
              ) : (
                <>
                  <span>Have an account?</span>
                  <button
                    type="button"
                    className="link-btn"
                    onClick={() => {
                      setMode('login')
                      setErrorMessage('')
                    }}
                  >
                    Sign in
                  </button>
                </>
              )}
            </div>

            <div className="auth-terms">
              <Link to="/">Terms & Conditions</Link>
            </div>
          </div>
        </div>


      </div>
    </div>
  )
}
