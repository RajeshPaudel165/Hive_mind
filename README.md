# HIVE BRAIN (Hackathon Project)

## Overview
HIVE BRAIN is an agentic harness that provides users with a proactive, stateful AI companion. It moves beyond standard chatbots by p>

## Core Architecture
*   **Infrastructure (The Compute):** Dedalus Cloud Services (DCS). We spin up dedicated Linux microVMs for each user to guarantee 1>
*   **Orchestration (The Brain):** OpenClaw. Acts as the gateway and routing layer on the Dedalus VM, connecting the LLM to messagin>
*   **Memory (The Context):** MemPalace. Runs locally on the Dedalus VM (using ChromaDB and SQLite) to provide structured, persisten>
*   **Interface:** Telegram (primary MVP focus for easy webhook integration).
*   **Ingestion:** A simple Chrome Extension that sends web dumps to the VM's MemPalace instance.

## Key Workflows
1.  **Provisioning:** A central Harness App uses the Dedalus SDK to spin up a new microVM when a user signs up.
2.  **Daily Check-ins:** Background scripts on the Dedalus VM use MemPalace data to prompt OpenClaw to send proactive messages to th>
3.  **Local RAG:** OpenClaw uses MemPalace MCP tools to answer questions based on user-provided context.

## Goal_view
 Phase 1: Onboarding & Provisioning
  The goal here is to show off the Dedalus microVM provisioning.

   1. The Harness Dashboard (Web UI): The user goes to your web app (e.g., hivebrain.dev).
   2. Sign Up: They enter their name and click a big button: "Deploy My Brain."
   3. The Backend Magic:
      * Your Next.js/Python backend calls the Dedalus SDK.
      * Dedalus spins up a new Ubuntu microVM (e.g., IP: 192.168.1.50).
      * Your backend runs a setup script on that VM to start OpenClaw, MemPalace, and the Telegram listener.
   4. The Handshake: The Harness Dashboard gives the user a unique Telegram bot link or QR code and a secret "pairing code" (e.g.,
      HIVE-1234).

  Phase 2: Connecting the Agent
  The goal here is to establish the Telegram connection and initialize MemPalace.

   1. Telegram Open: The user opens Telegram, starts a chat with the bot, and types their pairing code: /start HIVE-1234.
   2. OpenClaw Routing: OpenClaw running on their specific Dedalus VM receives this webhook. It verifies the code.
   3. The First Memory: The agent responds: "Hello! I'm your Hive Brain. I live on a private, isolated server just for you. What is
      your primary goal right now?"
   4. MemPalace Storage: The user replies: "I want to learn Fourier Analysis in 30 days." OpenClaw uses the MemPalace MCP tool to
      create a new "Room" (Project) in its local database called Fourier_Analysis and saves that goal verbatim.

  Phase 3: The Chrome Extension (Data Ingestion)
  The goal here is to show how easy it is to dump knowledge into the isolated VM.

   1. Browsing: The user is on a desktop reading a complex Wikipedia article about mathematics.
   2. The Dump: They click your "Hive Brain" Chrome Extension. They highlight some text and click "Send to Brain."
   3. Direct to VM: The extension sends a POST request directly to the IP address of the user's specific Dedalus VM (or a routed
      subdomain like user1.hivebrain.dev).
   4. MemPalace Ingestion: The VM receives the text and uses MemPalace to store it in the Fourier_Analysis Room.

  Phase 4: Proactive Check-in (The "Wow" Moment)
  The goal here is to prove the agent isn't just a reactive chatbot.

   1. The Background Script: A cron job on the Dedalus VM runs every hour. It checks MemPalace and sees: "Goal: Learn Fourier
      Analysis (Day 1). Needs a check-in."
   2. The Trigger: The script sends a system prompt to OpenClaw: "Review the user's recent MemPalace dumps regarding Fourier Analysis
      and send them a motivational summary."
   3. The Message: The user's phone buzzes. It's Telegram: "Hey! I saw you dumped some great notes on Sine Waves earlier. Do you have
      10 minutes right now to review them? I can quiz you!"

