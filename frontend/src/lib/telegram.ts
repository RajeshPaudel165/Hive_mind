import type { TelegramUserConfig } from '../types/telegramConfig'

export type CreateTelegramBotResponse = {
  botId: string
  botUsername: string
  botToken: string
  botName: string
}

type CreateTelegramBotRequest = {
  userEmail: string
  agentName: string
  config: TelegramUserConfig
}

function getCreateBotEndpoint(config: TelegramUserConfig): string {
  return config.registrationEndpoint.trim() || '/api/bots/create'
}

export async function createTelegramBot(
  params: CreateTelegramBotRequest,
): Promise<CreateTelegramBotResponse> {
  const { userEmail, agentName, config } = params

  const response = await fetch(getCreateBotEndpoint(config), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      userEmail,
      agentName,
      apiId: config.apiId,
      apiHash: config.apiHash,
      sessionString: config.sessionString,
      appTitle: config.appTitle,
      shortName: config.shortName,
    }),
  })

  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || 'Failed to create Telegram bot')
  }

  const data = (await response.json()) as Partial<CreateTelegramBotResponse>

  if (!data.botId || !data.botUsername || !data.botToken || !data.botName) {
    throw new Error('Telegram bot creation response was incomplete')
  }

  return data as CreateTelegramBotResponse
}
