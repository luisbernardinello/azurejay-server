<p align="center">
  <a href="#"><img src="assets/azurejay.png" height="200" /></a>
  <br/>
  <font size="6"><b>AzureJay Server</b></font>
  <br/>
  <em>An AI tutor to help you sound more natural when speaking English</em>
  <br/><br/>
  <a href="#"><img src="https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white" /></a>
  <a href="#"><img src="https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white" /></a>
  <a href="#"><img src="https://img.shields.io/badge/LangGraph-1C3C3C?logo=langgraph&logoColor=white" /></a>
  <a href="#"><img src="https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white" /></a>
  <a href="#"><img src="https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white" /></a>
  <a href="#"><img src="https://img.shields.io/badge/Redis-DC382D?logo=redis&logoColor=white" /></a>
</p>


<hr/>

## About

AzureJay, represented by an Atlantic Bird mascot, is a conversational language learning app designed to provide an efficient learning experience through AI-powered interactions. The primary focus is helping users make their English responses sound more natural and fluent.

<details open="open">
  <summary><b>📑 Table of Contents</b></summary>
  
  - [Features](#-features)
  - [Architecture](#-architecture)
    - [Architecture Overview](#architecture-overview)
    - [Pipeline Stages](#pipeline-stages)
  - [Tech Stack](#-tech-stack)
  - [Getting Started](#-getting-started)
    - [Installation](#installation)
    - [Running with Docker](#running-with-docker)
    - [Running Tests](#running-tests)
  - [License](#-license)
  
</details>

## Features

<table>
  <tr>
    <td>🎙️</td>
    <td><b>Voice-First Interaction</b><br/>Full support for audio-based conversations, using <b>Groq (Whisper)</b> for fast Speech-to-Text and <b>ElevenLabs</b> for Text-to-Speech.</td>
  </tr>
  <tr>
    <td>🗣️</td>
    <td><b>Conversation-Based Learning</b><br/>Natural dialogue with AI tutor for immersive language practice.</td>
  </tr>
  <tr>
    <td>🔍</td>
    <td><b>Dual-Layer Error Detection</b><br/>Pre-processing pipeline analyzes user input using <b>LanguageTool API</b> for syntactic errors and a specialist LLM for semantic errors.</td>
  </tr>
  <tr>
    <td>🧠</td>
    <td><b>Reasoning Agent (AFM)</b><br/>Primary agent that uses a Plan-Reflect-Act cycle for intelligent responses.</td>
  </tr>
  <tr>
    <td>🎯</td>
    <td><b>Personalized Learning</b><br/>Adapts and maintains long-term memory of your interests and learning patterns.</td>
  </tr>
  <tr>
    <td>💾</td>
    <td><b>Persistent Memory</b><br/><b>PostgreSQL</b> for core data (users, conversations, messages) and <b>Redis</b> for long-term agent memory (user profiles, corrections). Uses a write-through cache strategy, writing to both databases simultaneously to ensure data consistency and low-latency access.</td>
  </tr>
  <tr>
    <td>🔗</td>
    <td><b>Contextual Research</b><br/>Integrated <b>Tavily Search API</b> to gather real-time, external information.</td>
  </tr>
</table>

## Architecture

### Architecture Overview

AzureJay uses a direct and efficient processing pipeline that feeds a central reasoning agent:

```
┌─────────────────────────────────────────────────────────────────┐
│                         Audio Input                             │
└────────────────────────────┬────────────────────────────────────┘
                             │
                ┌────────────▼────────────────┐
                │    Audio Pipeline           │
                │ (Groq STT / ElevenLabs TTS) │
                └────────────┬────────────────┘
                             │
                        Text Message
                             │
                ┌────────────▼───────────────┐
                │  Pre-processing Graph      │
                │      (LangGraph)           │
                │ src/agent/grammar_pipe.py  │
                └────────────┬───────────────┘
                             │
                   ┌─────────┴──────────┐
                   │                    │
          ┌────────▼──────────┐  ┌──────▼───────────┐
          │ 1.syntactic_check │  │ 2.semantic_check │
          │  (LanguageTool)   │  │ (Specialist LLM) │
          └────────┬──────────┘  └─────┬────────────┘
                   │                   │
                   └─────────┬─────────┘
                             │
            Text + Syntactic/Semantic Analysis
                             │
                ┌────────────▼───────────────┐
                │   Main Agent "Rachel"      │
                │  src/agent/afm_executor.py │
                │    (Plan-Reflect-Act)      │
                └────────────┬───────────────┘
                             │
              Decides: <final_answer> or <tool_call>
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
   ┌────▼─────┐       ┌──────▼──────┐      ┌──────▼──────────┐
   │WebSearch │       │  Update...  │      │ SaveGrammar...  │
   │ (Tavily) │       │   (Redis)   │      │  (PostgreSQL)   │
   └──────────┘       └─────────────┘      └─────────────────┘
                          Tools
```

### Pipeline Stages

#### 1. Audio Pipeline (Optional)

If the input is audio, it is first transcribed to text via **Groq Whisper**. The final response is similarly converted back to speech via **ElevenLabs**.

#### 2. Pre-processing Graph (LangGraph)

The user's text is analyzed by a `StateGraph`:

- **Node 1: `syntactic_check_node`**  
  Uses the `LanguageToolAPI` to catch explicit grammatical errors (syntax).

- **Node 2: `semantic_check_node`**  
  Uses a specialist LLM (`llama-3.3-70b-versatile`) to find semantic or usage errors that "sound unnatural," even if grammatically correct.

#### 3. Main Agent (AFM Executor)

The main agent receives the user's original input and the analyses from the previous stages. It then generates a `<plan>` to decide the next action:

- **Call Tools**: If the user mentioned new interests (`UpdateUserProfile`), made a correctable error (`SaveGrammarCorrection`), or asked a question (`WebSearch`).
- **Generate Response**: If no tools are needed, it generates the `<final_answer>` to continue the conversation.

---

## 🛠️ Tech Stack

| Category | Technology |
|----------|-----------|
| **Backend** | FastAPI |
| **Agent Orchestration** | LangGraph |
| **LLMs & STT** | Groq (Llama, Whisper) |
| **TTS** | ElevenLabs |
| **Primary Database** | PostgreSQL |
| **Agent Memory / Cache** | Redis |
| **Web Search** | Tavily Search |
| **Grammar Analysis** | LanguageTool |
| **Containerization** | Docker & Docker Compose |

---

## 🚀 Getting Started

### Installation

1. **Clone the repository**

```bash
git clone https://github.com/luisbernardinello/AzureJay-Server.git
cd AzureJay
```

2. **Install dependencies**

```bash
pip install -r requirements.txt
```

### Running with Docker

1. **Install Docker Desktop**

2. **Start all services**

```bash
docker-compose up --build
```

3. **Stop all services**

```bash
docker-compose down
```

### Running Tests

Execute the test suite:

```bash
pytest
```


## License

AzureJay is licensed under the **AGPL-3.0** license.
