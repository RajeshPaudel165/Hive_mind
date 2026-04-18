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

