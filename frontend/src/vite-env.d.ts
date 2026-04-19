/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_FIREBASE_API_KEY: string
  readonly VITE_FIREBASE_AUTH_DOMAIN: string
  readonly VITE_FIREBASE_PROJECT_ID: string
  readonly VITE_FIREBASE_STORAGE_BUCKET: string
  readonly VITE_FIREBASE_MESSAGING_SENDER_ID: string
  readonly VITE_FIREBASE_APP_ID: string
  readonly VITE_FIREBASE_MEASUREMENT_ID: string
  readonly VITE_HIVE_API_BASE: string
  readonly VITE_TELEGRAM_API_ID: string
  readonly VITE_TELEGRAM_API_HASH: string
  readonly VITE_TELEGRAM_APP_TITLE: string
  readonly VITE_TELEGRAM_SHORT_NAME: string
  readonly VITE_TELEGRAM_REGISTRATION_ENDPOINT: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
