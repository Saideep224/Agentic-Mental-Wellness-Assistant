# Chat Pipeline Flow

The Esona conversational engine is orchestrated using a multi-agent LangGraph workflow. This ensures structured processing of user inputs, context retrieval, safety checks, and response formulation.

## Message Orchestration Pipeline

```
     User Message
          │
          ▼
┌──────────────────┐
│  Cognitive Node  │ ──> Analyzes emotion, safety level, and intent.
└──────────────────┘
          │
          ▼
┌──────────────────┐
│   Memory Node    │ ──> Retrieves long-term memories and graph relationships.
└──────────────────┘
          │
          ▼
┌──────────────────┐
│  Response Node   │ ──> Formulates response, applies repetitiveness checks.
└──────────────────┘
          │
          ▼
    Final Response
```

### Step 1: Cognitive Analysis
- Exposes user text to the [Cognitive Analyzer LLM](file:///e:/2026%20research%20intern/esona/backend/app/chatbot/pipeline.py#L77-L100).
- Simulates multi-agent reasoning:
  - **Safety Agent**: Checks for self-harm or crisis keywords. If flagged, bypasses standard response and triggers crisis resources.
  - **Emotion Agent**: Classifies raw sentiment using the MentalBERT service.
  - **Intent Agent**: Identifies whether the user is greeting, asking for advice, venting, or ending the chat.
  - **Personality Agent**: Retrieves the user's communication style (e.g. casual vs. warm) from their profile.

### Step 2: Context Retrieval
- Exposes user text to the [Memory Agent](file:///e:/2026%20research%20intern/esona/backend/app/agents/memory_agent.py).
- Queries the Vector Database / Memories table to pull the top 5 most relevant historical observations.
- Queries the Knowledge Graph to extract relationships containing entities present in the user's input.
- Reads previous conversation summaries to remember historical context.

### Step 3: Response Generation
- Hands combined contexts to the [Response Agent](file:///e:/2026%20research%20intern/esona/backend/app/agents/response_agent.py).
- Generates a response draft utilizing the user's preferred communication style, humor settings, and length.
- Applies a **repetition guard** checking against a cache of the last 20 responses to prevent robotic loops.
- Streams the final response to the user via Server-Sent Events (SSE).
