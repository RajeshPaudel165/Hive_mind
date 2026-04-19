export type Agent = {
  id: string
  name: string
  role: string
  botId: string
  botUsername: string
  botToken: string
  deliveryStatus: 'sent' | 'pending'
  // Performance metrics
  messagesSent?: number
  averageResponseTime?: number // in milliseconds
  telegramConnectionStatus?: 'connected' | 'disconnected' | 'error'
  lastActivityAt?: string // ISO timestamp
}
