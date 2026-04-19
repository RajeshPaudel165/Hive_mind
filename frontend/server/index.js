import cors from 'cors'
import dotenv from 'dotenv'
import express from 'express'
import { TelegramClient } from 'telegram'
import { StringSession } from 'telegram/sessions'

dotenv.config()

const app = express()
const port = Number(process.env.PORT || 8787)

app.use(cors())
app.use(express.json({ limit: '1mb' }))

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function randomSuffix() {
  return Math.random().toString(36).slice(2, 8)
}

function normalizeBotName(name) {
  const trimmed = String(name ?? '').trim()
  if (trimmed) {
    return trimmed
  }

  return `HiveMind ${randomSuffix().toUpperCase()}`
}

function generateBotUsername(seed) {
  const base = String(seed ?? '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '')
    .slice(0, 12) || 'hivemind'

  return `${base}_${randomSuffix()}_bot`
}

function extractBotToken(text) {
  const match = String(text ?? '').match(/\b\d{5,}:[A-Za-z0-9_-]+\b/)
  return match ? match[0] : ''
}

async function fetchBotFatherMessages(client) {
  const messages = await client.getMessages('BotFather', { limit: 10 })
  return Array.isArray(messages) ? messages : [messages]
}

async function waitForBotFatherReply(client, timeoutMs = 30000) {
  const startedAt = Date.now()

  while (Date.now() - startedAt < timeoutMs) {
    const messages = await fetchBotFatherMessages(client)
    const newest = messages
      .filter((message) => typeof message?.message === 'string')
      .sort((left, right) => Number(right.id ?? 0) - Number(left.id ?? 0))[0]

    if (newest?.message) {
      return String(newest.message)
    }

    await sleep(1000)
  }

  throw new Error('Timed out waiting for BotFather')
}

app.get('/health', (_request, response) => {
  response.json({ ok: true })
})

app.post('/api/bots/create', async (request, response) => {
  const {
    apiId,
    apiHash,
    sessionString,
    agentName,
  } = request.body ?? {}

  if (!apiId || !apiHash || !sessionString) {
    return response.status(400).json({
      error: 'Telegram API ID, API hash, and session string are required.',
    })
  }

  const botName = normalizeBotName(agentName)
  const client = new TelegramClient(
    new StringSession(sessionString),
    Number(apiId),
    String(apiHash),
    { connectionRetries: 5 },
  )

  try {
    await client.connect()

    const botFather = 'BotFather'
    await client.sendMessage(botFather, { message: '/newbot' })
    await waitForBotFatherReply(client)

    await client.sendMessage(botFather, { message: botName })
    await waitForBotFatherReply(client)

    let botUsername = generateBotUsername(botName)
    let token = ''

    for (let attempt = 0; attempt < 5 && !token; attempt += 1) {
      await client.sendMessage(botFather, { message: botUsername })
      const reply = await waitForBotFatherReply(client, 60000)

      if (/already taken/i.test(reply)) {
        botUsername = generateBotUsername(botName)
        continue
      }

      token = extractBotToken(reply)

      if (!token) {
        botUsername = generateBotUsername(botName)
      }
    }

    if (!token) {
      throw new Error('BotFather did not return a token. Check your Telegram session and try again.')
    }

    response.json({
      botId: token.split(':')[0],
      botUsername,
      botToken: token,
      botName,
    })
  } catch (error) {
    response.status(500).json({
      error: error instanceof Error ? error.message : 'Failed to create bot',
    })
  } finally {
    await client.disconnect().catch(() => {})
  }
})

app.listen(port, () => {
  console.log(`Telegram bot server running on http://localhost:${port}`)
})