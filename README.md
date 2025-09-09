<p align="center">
  <a href="#"><img src="src/assets/azurejay.png" height="250" /></a>
  <br/>
  <font size="6"><b>AzureJay Server</b></font>
  <br/>
  <em>An AI tutor to help you sound more natural when speaking English</em>
  <br/><br/>
  <a href="#"><img src="https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white" /></a>
  <a href="#"><img src="https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white" /></a>
  <a href="#"><img src="https://img.shields.io/badge/LangGraph-1C3C3C?logo=langgraph&logoColor=white" /></a>
  <a href="#"><img src="https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white" /></a>
</p>

<hr/>

## About

AzureJay, represented by an Atlantic Bird mascot, is a conversational language learning app designed to provide an efficient learning experience through AI-powered interactions. The app uses a Supervisor architecture with multiple specialized agents to detect grammar and vocabulary errors, gather contextual information, and provide corrections and explanations. The primary focus is helping users make their English responses sound more natural and fluent.

<details open="open">
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about">About</a>
    </li>
    <li>
      <a href="#features">Features</a>
    </li>
    <li>
      <a href="#supervisor-architecture">Supervisor Architecture</a>
      <ul>
        <li><a href="#architecture-overview">Architecture Overview</a></li>
        <li><a href="#specialized-agents">Specialized Agents</a></li>
        <li><a href="#workflow-orchestration">Workflow Orchestration</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a></li>
    <li>
    <li>
      <a href="#license">License</a>
    </li>
  </ol>
</details>

## Features

- 🗣️ **Conversation-Based Learning**: Natural dialogue with AI tutor
- 🔍 **Multi-Layer Error Detection**: Real-time grammar and semantic correction using LanguageTool API and LLM verification
- 🧠 **Supervisor Architecture**: Workflow orchestration with specialized agents for different tasks
- 🎯 **Personalized Learning**: Adapts amd maintains long-term memory of your interests
- 🔗 **Contextual Research**: Web search integration for real-time information gathering
- 💾 **Persistent Memory**: Long-term storage of user profiles

## Supervisor Architecture

### Architecture Overview

AzureJay is built on an Supervisor architecture that orchestrates multiple specialized agents to provide language learning support:

```
                                                      +-----------+
                                                      | __start__ |
                                                      +-----------+
                                                             *
                                                             *
                                                             *
                                                  +-------------------+
                                               ...| supervisor        |....
                                     ..........  *+-------------------+.   .........
                          ...........       *****            *          .....       ..........
                ..........             *****                *                ....             .........
          ......                    ***                     *                    ...                   .....
+---------+           +----------------+           +----------------+           +--------------+           +----------------+
| __end__ |           | correction     |           | researcher     |           | responder    |           | web_search_api |
+---------+           +----------------+           +----------------+           +--------------+           +----------------+
```

### Specialized Agents

#### 🎯 **Supervisor Agent**

- **Role**: Central workflow orchestrator
- **Responsibilities**:
  - Routes tasks to appropriate specialists based on current state
  - Ensures efficient workflow without unnecessary steps
  - Maintains transparency in decision-making process

#### ✏️ **Correction Agent**

- **Role**: Multi-layer grammar and semantic correction specialist
- **Layer 1 - Syntax Analysis**: Uses LanguageTool API for comprehensive grammar checking
- **Layer 2 - Semantic Verification**: Employs LLM verification for contextual and semantic corrections
- **Layer 3 - Synthesis**: Combines suggestions from both layers for optimal corrections

#### 🔍 **Research Agent**

- **Role**: Information gathering and fact-finding specialist
- **Capabilities**:
  - Web search integration using Tavily Search API
  - Updated information retrieval
  - Source credibility assessment
  - Structured information presentation
- **Activation**: Called only when users ask direct questions

#### 🤖 **Responder Agent (Subgraph)**

- **Role**: Conversational AI tutor with memory management
- **Components**:
  - **Memory Management**: Long-term storage of user profiles and correction history
  - **Personalized Responses**: Adapts to user interests and learning progress
  - **TrustCall Integration**: Structured information extraction and storage
  - **Contextual Awareness**: Incorporates corrections and research into responses

### Workflow Orchestration

1. **Input Processing**: User message enters the system
2. **Grammar Correction**: Supervisor routes to Correction Agent
3. **Research Evaluation**: Determines if external information gathering is needed
4. **Response Generation**: Routes to Responder subgraph for final interaction
5. **Memory Updates**: Automatically saves user profiles and correction history

**Key Benefits:**

- **Accuracy**: Multi-layer correction ensures high-quality feedback
- **Personalization**: Long-term memory enables personalized learning experiences

### Getting Started

#### Clone the repository

```bash
git clone https://github.com/luisbernardinello/AzureJay-Server.git
cd AzureJay
```

#### Install all dependencies.

- Run `pip install -r requirements-dev.txt`

#### How to run app. Using Docker with PostgreSQL.

- Install Docker Desktop
- Run `docker-compose up --build`
- Run `docker-compose down` to stop all services

#### How to run tests.

- Run `pytest` to run all tests


## License

AzureJay is licensed under the AGPL-3.0 license.