import type { Agent } from '../types/agent'

const DEFAULT_HIVE_API_BASE = 'http://127.0.0.1:8010'

export const hiveApiBase =
  import.meta.env.VITE_HIVE_API_BASE?.replace(/\/$/, '') || DEFAULT_HIVE_API_BASE

type CreateHiveAgentInput = {
  userId: string
  userEmail: string
  agentName: string
  agentRole: string
  telegramBotToken: string
}

type HiveAgentResponse = {
  agent_id: string
  user_id?: string | null
  user_name: string
  agent_name: string
  agent_role: string
  telegram_bot_configured: boolean
  user_runtime?: {
    provider?: string
    machine_id?: string | null
    status?: string
    ready?: boolean
    mode?: string
  } | null
  telegram_start_instruction?: string
  worker_command?: string
  openclaw?: {
    reachable?: boolean
    managed_pid?: number | null
    started?: boolean
    message?: string
  }
  telegram_worker?: {
    running?: boolean
    pid?: number | null
    log_path?: string
  }
}

export type OpenClawHealth = {
  reachable?: boolean
  managed_pid?: number | null
  managed_running?: boolean
  error?: string
}

export type TelegramWorkerStatus = {
  agent_id: string
  running: boolean
  pid: number | null
  exit_code?: number | null
  log_path?: string
}

export async function createHiveAgent(
  input: CreateHiveAgentInput,
): Promise<Agent> {
  const response = await fetch(`${hiveApiBase}/agents`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: input.userId,
      user_name: input.userEmail,
      agent_name: input.agentName,
      agent_role: input.agentRole,
      telegram_bot_token: input.telegramBotToken,
      start_openclaw: true,
      start_telegram_worker: true,
    }),
  })

  const data = (await response.json().catch(() => null)) as
    | HiveAgentResponse
    | { detail?: string }
    | null

  if (!response.ok) {
    const detail =
      data && 'detail' in data && typeof data.detail === 'string'
        ? data.detail
        : `HIVE backend returned ${response.status}`
    throw new Error(detail)
  }

  if (!data || !('agent_id' in data)) {
    throw new Error('HIVE backend returned an invalid agent response.')
  }

  const botId = input.telegramBotToken.split(':')[0] ?? ''

  return {
    id: data.agent_id,
    hiveAgentId: data.agent_id,
    userId: data.user_id ?? input.userId,
    name: data.agent_name,
    role: data.agent_role,
    runtimeProvider: data.user_runtime?.provider,
    runtimeMachineId: data.user_runtime?.machine_id,
    runtimeStatus: data.user_runtime?.status,
    botId,
    botUsername: '',
    botToken: input.telegramBotToken,
    deliveryStatus: data.telegram_bot_configured ? 'sent' : 'pending',
    telegramConnectionStatus: data.telegram_worker?.running
      ? 'connected'
      : 'disconnected',
    telegramStartInstruction: data.telegram_start_instruction,
    workerCommand: data.worker_command,
    openclawReachable: data.openclaw?.reachable ?? false,
    openclawPid: data.openclaw?.managed_pid ?? null,
    workerPid: data.telegram_worker?.pid ?? null,
    workerLogPath: data.telegram_worker?.log_path,
  }
}


export async function getOpenClawHealth(): Promise<OpenClawHealth> {
  const response = await fetch(`${hiveApiBase}/integrations/openclaw/health`)
  const data = (await response.json().catch(() => null)) as OpenClawHealth | null

  if (!response.ok) {
    throw new Error(`HIVE backend returned ${response.status}`)
  }

  return data ?? { reachable: false }
}


export async function getTelegramWorkerStatus(
  agentId: string,
): Promise<TelegramWorkerStatus> {
  const response = await fetch(`${hiveApiBase}/agents/${agentId}/telegram/status`)
  const data = (await response.json().catch(() => null)) as
    | TelegramWorkerStatus
    | { detail?: string }
    | null

  if (!response.ok) {
    const detail =
      data && 'detail' in data && typeof data.detail === 'string'
        ? data.detail
        : `HIVE backend returned ${response.status}`
    throw new Error(detail)
  }

  if (!data || !('agent_id' in data)) {
    throw new Error('HIVE backend returned an invalid Telegram worker status.')
  }

  return data
}


export async function deleteHiveAgent(agentId: string): Promise<void> {
  const response = await fetch(`${hiveApiBase}/agents/${agentId}`, {
    method: 'DELETE',
  })

  if (response.status === 404) {
    return
  }

  if (!response.ok) {
    const data = (await response.json().catch(() => null)) as
      | { detail?: string }
      | null
    throw new Error(data?.detail || `HIVE backend returned ${response.status}`)
  }
}
