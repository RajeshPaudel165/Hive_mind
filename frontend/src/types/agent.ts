export type Agent = {
  id: string
  hiveAgentId?: string
  userId?: string | null
  name: string
  role: string
  runtimeProvider?: string
  runtimeMachineId?: string | null
  runtimeStatus?: string
  botId: string
  botUsername: string
  botToken: string
  deliveryStatus: 'sent' | 'pending'
  // Performance metrics
  messagesSent?: number
  averageResponseTime?: number // in milliseconds
  telegramConnectionStatus?: 'connected' | 'disconnected' | 'error'
  lastActivityAt?: string // ISO timestamp
  telegramStartInstruction?: string
  workerCommand?: string
  openclawReachable?: boolean
  openclawPid?: number | null
  workerPid?: number | null
  workerLogPath?: string
}
