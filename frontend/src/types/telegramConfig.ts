export type TelegramUserConfig = {
  apiId: string
  apiHash: string
  appTitle: string
  shortName: string
  registrationEndpoint: string
  sessionString: string
}

export const defaultTelegramUserConfig: TelegramUserConfig = {
  apiId: '',
  apiHash: '',
  appTitle: import.meta.env.VITE_TELEGRAM_APP_TITLE ?? '',
  shortName: import.meta.env.VITE_TELEGRAM_SHORT_NAME ?? '',
  registrationEndpoint: import.meta.env.VITE_TELEGRAM_REGISTRATION_ENDPOINT ?? '',
  sessionString: '',
}
