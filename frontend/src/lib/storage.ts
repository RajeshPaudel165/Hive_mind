import type { Agent } from '../types/agent'
import {
  defaultTelegramUserConfig,
  type TelegramUserConfig,
} from '../types/telegramConfig'

const LOGIN_STORAGE_KEY = 'hivemind-user-email'
const TELEGRAM_CONFIG_PREFIX = 'hivemind-telegram-config'
const AGENTS_PREFIX = 'hivemind-agents'

function normalizeUserKey(userEmail: string): string {
  return userEmail.trim().toLowerCase()
}

function getAgentsStorageKey(userEmail: string): string {
  return `${AGENTS_PREFIX}:${normalizeUserKey(userEmail)}`
}

function getTelegramStorageKey(userEmail: string): string {
  return `${TELEGRAM_CONFIG_PREFIX}:${normalizeUserKey(userEmail)}`
}

export function loadAgentsFromStorage(userEmail: string): Agent[] {
  const key = getAgentsStorageKey(userEmail)
  const raw = localStorage.getItem(key)
  if (!raw) {
    return []
  }

  try {
    const parsed = JSON.parse(raw)

    if (!Array.isArray(parsed)) {
      return []
    }

    return parsed.filter(
      (item): item is Agent =>
        typeof item?.id === 'string' &&
        typeof item?.name === 'string' &&
        typeof item?.role === 'string' &&
        typeof item?.botId === 'string' &&
        typeof item?.botUsername === 'string' &&
        typeof item?.botToken === 'string' &&
        (item?.deliveryStatus === 'sent' || item?.deliveryStatus === 'pending'),
    )
  } catch {
    return []
  }
}

export function saveAgentsToStorage(userEmail: string, agents: Agent[]): void {
  const key = getAgentsStorageKey(userEmail)
  localStorage.setItem(key, JSON.stringify(agents))
}

export function loadUserEmailFromStorage(): string {
  return localStorage.getItem(LOGIN_STORAGE_KEY) ?? ''
}

export function saveUserEmailToStorage(email: string): void {
  localStorage.setItem(LOGIN_STORAGE_KEY, email)
}

export function clearUserEmailFromStorage(): void {
  localStorage.removeItem(LOGIN_STORAGE_KEY)
}

export function loadTelegramConfigFromStorage(
  userEmail: string,
): TelegramUserConfig {
  const key = getTelegramStorageKey(userEmail)
  const raw = localStorage.getItem(key)

  if (!raw) {
    return defaultTelegramUserConfig
  }

  try {
    const parsed = JSON.parse(raw)

    if (
      typeof parsed?.apiId === 'string' &&
      typeof parsed?.apiHash === 'string' &&
      typeof parsed?.appTitle === 'string' &&
      typeof parsed?.shortName === 'string' &&
      typeof parsed?.registrationEndpoint === 'string' &&
      typeof parsed?.sessionString === 'string'
    ) {
      return parsed
    }
  } catch {
    return defaultTelegramUserConfig
  }

  return defaultTelegramUserConfig
}

export function saveTelegramConfigToStorage(
  userEmail: string,
  config: TelegramUserConfig,
): void {
  const key = getTelegramStorageKey(userEmail)
  localStorage.setItem(key, JSON.stringify(config))
}
