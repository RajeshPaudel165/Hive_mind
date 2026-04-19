function randomSuffix(): string {
  return Math.random().toString(36).slice(2, 8)
}

export function generateRandomBotIdentity() {
  const suffix = randomSuffix()
  const agentName = `HiveMind ${suffix.toUpperCase()}`
  const botUsername = `hivemind_${suffix}_bot`

  return {
    agentName,
    botUsername,
  }
}

export function buildBotFatherNewBotCommands(params: {
  botName: string
  botUsername: string
}): string {
  const { botName, botUsername } = params
  return ['/makebot', botName.trim(), botUsername.trim().replace('@', '')].join('\n')
}
