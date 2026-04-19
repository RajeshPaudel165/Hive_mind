import { useEffect, useState } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { ProtectedRoute } from './components/ProtectedRoute'
import {
  loadAgentsFromStorage,
  saveAgentsToStorage,
} from './lib/storage'
import {
  deleteAgentFromFirebase,
  loadAgentsFromFirebase,
  loginWithEmailPassword,
  logoutFromFirebase,
  registerWithEmailPassword,
  subscribeToFirebaseAuth,
} from './lib/firebase'
import { CreateAgentPage } from './pages/CreateAgentPage'
import { DashboardPage } from './pages/DashboardPage'
import { LandingPage } from './pages/LandingPage'
import { LoginPage } from './pages/LoginPage'
import { SettingsProfilePage } from './pages/SettingsProfilePage'
import { SettingsAPIPage } from './pages/SettingsAPIPage'
import { deleteHiveAgent } from './lib/hiveBackend'
import type { Agent } from './types/agent'
import './App.css'

function App() {
  const [authReady, setAuthReady] = useState(false)
  const [userId, setUserId] = useState('')
  const [userEmail, setUserEmail] = useState('')
  const [agents, setAgents] = useState<Agent[]>([])
  const isLoggedIn = Boolean(userId)

  useEffect(() => {
    const unsubscribe = subscribeToFirebaseAuth((user) => {
      if (!user) {
        setUserId('')
        setUserEmail('')
        setAgents([])
        setAuthReady(true)
        return
      }

      setUserId(user.uid)
      setUserEmail(user.email ?? '')

      void (async () => {
        try {
          const remoteAgents = await loadAgentsFromFirebase(user.uid)
          setAgents(remoteAgents)
        } catch {
          setAgents(loadAgentsFromStorage(user.email ?? user.uid))
        } finally {
          setAuthReady(true)
        }
      })()
    })

    return unsubscribe
  }, [])

  useEffect(() => {
    if (userEmail) {
      saveAgentsToStorage(userEmail, agents)
    }
  }, [agents, userEmail])

  const handleLogin = async (email: string, password: string) => {
    await loginWithEmailPassword(email, password)
  }

  const handleCreateAccount = async (email: string, password: string) => {
    await registerWithEmailPassword(email, password)
  }

  const handleLogout = async () => {
    await logoutFromFirebase()
  }

  const handleCreateAgent = (newAgent: Agent) => {
    setAgents((current) => [newAgent, ...current])
  }

  const handleDeleteAgent = async (agent: Agent) => {
    const agentId = agent.hiveAgentId || agent.id
    await deleteHiveAgent(agentId)
    await deleteAgentFromFirebase({ userId, agentId: agent.id })
    setAgents((current) => current.filter((item) => item.id !== agent.id))
  }

  if (!authReady) {
    return (
      <div className="page-bg">
        <div className="page-shell single-col-shell">
          <section className="card auth-card">
            <p className="eyebrow dark-eyebrow">Loading</p>
            <h1>Preparing your workspace...</h1>
          </section>
        </div>
      </div>
    )
  }

  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route
        path="/login"
        element={
          <LoginPage
            onLogin={handleLogin}
            onCreateAccount={handleCreateAccount}
          />
        }
      />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute isLoggedIn={isLoggedIn}>
            <DashboardPage
              userEmail={userEmail}
              agents={agents}
              onLogout={handleLogout}
              onDeleteAgent={handleDeleteAgent}
            />
          </ProtectedRoute>
        }
      />
      <Route
        path="/agents/new"
        element={
          <ProtectedRoute isLoggedIn={isLoggedIn}>
            <CreateAgentPage
              userId={userId}
              userEmail={userEmail}
              onCreateAgent={handleCreateAgent}
            />
          </ProtectedRoute>
        }
      />
      <Route
        path="/settings/profile"
        element={
          <ProtectedRoute isLoggedIn={isLoggedIn}>
            <SettingsProfilePage
              userEmail={userEmail}
              onLogout={handleLogout}
            />
          </ProtectedRoute>
        }
      />
      <Route
        path="/settings/api"
        element={
          <ProtectedRoute isLoggedIn={isLoggedIn}>
            <SettingsAPIPage
              userEmail={userEmail}
              onLogout={handleLogout}
            />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
