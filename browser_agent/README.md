# Browser Agent

A minimal prototype of an AI-powered browser agent. Google Gemini (via the `google-genai` SDK) controls a real Chromium browser through Playwright, orchestrated by LangChain's ReAct agent framework.

---

## Project Structure

```
browser_agent/
├── agent.py          # Main entry point – LLM + tools + task
├── browser_tools.py  # BrowserController (Playwright wrapper)
├── requirements.txt  # Python dependencies
└── README.md
```

---

## Prerequisites

- Python 3.11+
- A **Google API key** with access to the Gemini API

---

## Installation

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Playwright's Chromium browser

```bash
playwright install chromium
```

### 3. Set your Google API key

```bash
export GOOGLE_API_KEY="your-google-api-key-here"
```

> You can obtain a key from [Google AI Studio](https://aistudio.google.com/app/apikey).

---

## Running the Agent

```bash
python agent.py
```

### What it does

1. Launches a visible Chromium browser window
2. Navigates to `https://example.com`
3. Reads the visible page text
4. Extracts and prints the main heading (`Example Domain`)
5. Closes the browser cleanly

---

## Configuration

| Variable | Description |
|---|---|
| `GOOGLE_API_KEY` | Your Google Gemini API key (required) |

The model is set to `gemini-1.5-flash` with `temperature=0` for deterministic output. You can change the model name in `agent.py`.

---

## Dependencies

| Package | Purpose |
|---|---|
| `langchain` | Agent framework & tool orchestration |
| `langchain-community` | Community integrations |
| `langchain-google-genai` | LangChain ↔ Gemini bridge |
| `google-genai` | Google Generative AI SDK |
| `playwright` | Browser automation (Chromium) |

---

## Troubleshooting

- **`GOOGLE_API_KEY` not set** – Run `export GOOGLE_API_KEY="..."` before `python agent.py`.
- **Chromium not found** – Run `playwright install chromium`.
- **Import errors** – Ensure all dependencies are installed with `pip install -r requirements.txt`.

---

---

# 🚀 Roadmap: From Prototype → Full-Featured AI Browser Agent

> This section is a complete engineering guide for evolving this minimal prototype into a production-grade AI browser agent — comparable to **Perplexity**, **Comet Browser**, **ChatGPT's browser tool**, or **Google's Project Mariner / Atlas**.

---

## Architecture Overview

A full AI browser agent has five core layers:

```
┌──────────────────────────────────────────────┐
│               User Interface                 │  ← Chat UI, streaming output
├──────────────────────────────────────────────┤
│              Orchestration Layer             │  ← Planner, memory, loop control
├──────────────────────────────────────────────┤
│                 LLM Core                     │  ← Gemini / GPT-4o / Claude
├──────────────────────────────────────────────┤
│              Tool / Skill Layer              │  ← Browser, search, code, files
├──────────────────────────────────────────────┤
│           Browser Execution Layer            │  ← Playwright / CDP / vision
└──────────────────────────────────────────────┘
```

---

## Phase 1 — Richer Browser Control

**Goal:** Make the agent capable of doing anything a human can do in a browser.

### Tools to add to `browser_tools.py`

| Tool | Description |
|---|---|
| `scroll(direction, amount)` | Scroll up/down by pixels |
| `type_text(selector, text)` | Type into an input field |
| `get_screenshot()` | Returns a base64 PNG of the viewport |
| `get_html(selector)` | Returns raw HTML of a specific element |
| `wait_for_element(selector)` | Wait until an element appears |
| `extract_links()` | Returns all `<a href>` links on the page |
| `fill_form(fields: dict)` | Fill multiple form fields at once |
| `press_key(key)` | Send keyboard events (Enter, Tab, Escape…) |
| `hover(selector)` | Hover over an element to trigger dropdowns |
| `new_tab(url)` | Open a new browser tab |
| `switch_tab(index)` | Switch between open tabs |
| `get_cookies()` | Return current session cookies |
| `run_js(script)` | Execute arbitrary JavaScript on the page |

### Implementation pattern

```python
def type_text(self, selector: str, text: str) -> str:
    try:
        self._page.fill(selector, text)
        return f"Typed into {selector}"
    except Exception as e:
        return f"Error typing into {selector}: {e}"

def get_screenshot(self) -> bytes:
    try:
        return self._page.screenshot(type="png")
    except Exception as e:
        return b""
```

---

## Phase 2 — Vision: Seeing the Browser Like a Human

**Goal:** Let the agent understand pages visually, not just as raw text. This is how **Comet Browser** and **Project Mariner** operate.

### Approach A: Screenshot + Multimodal LLM

Capture a screenshot and send it directly to Gemini Vision:

```python
import base64
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

def analyze_screenshot(screenshot_bytes: bytes, question: str) -> str:
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0)
    b64 = base64.b64encode(screenshot_bytes).decode()
    message = HumanMessage(content=[
        {"type": "text", "text": question},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
    ])
    return llm.invoke([message]).content
```

### Approach B: Set-of-Marks (SoM) Prompting

Number every interactive element in the screenshot with an overlay, then ask the LLM to pick a number. Used by **GPT-4V agents** and **Agent-E**.

```
[1] Search Box  [2] Sign In  [3] "Buy Now" button
```

### Approach C: Accessibility Tree (AXTree)

Use Playwright's accessibility snapshot — a structured JSON of every interactive element — as a lightweight alternative to screenshots:

```python
snapshot = page.accessibility.snapshot()
# Pass snapshot JSON to the LLM instead of full HTML
```

---

## Phase 3 — Planning & Multi-Step Reasoning

**Goal:** Upgrade from a single ReAct loop to a structured planner that can handle long, multi-step tasks reliably.

### ReAct (current) vs Planning Patterns

| Pattern | Complexity | Best for |
|---|---|---|
| **ReAct** (current) | Low | Simple 3–5 step tasks |
| **Plan-and-Execute** | Medium | Tasks with known sub-goals |
| **LangGraph** | High | Complex loops, branches, retries |
| **AutoGen / CrewAI** | High | Multi-agent coordination |

### Plan-and-Execute with LangGraph

```python
from langgraph.graph import StateGraph, END

def planner_node(state):
    # LLM generates a plan: ["step1", "step2", ...]
    ...

def executor_node(state):
    # Execute one step, observe result
    ...

def should_continue(state):
    return "executor" if steps_remain else END

graph = StateGraph(AgentState)
graph.add_node("planner", planner_node)
graph.add_node("executor", executor_node)
graph.add_edge("planner", "executor")
graph.add_conditional_edges("executor", should_continue)
```

### Self-Correction Loop

Add a `critic_node` that reviews each action's result and decides whether to retry, backtrack, or continue — a key feature of **Perplexity Pro** and **Atlas**.

---

## Phase 4 — Memory

**Goal:** Let the agent remember past sessions, user preferences, and contextual facts.

### Three types of memory

| Type | What it stores | Implementation |
|---|---|---|
| **Short-term** | Current session history | LangChain `ConversationBuffer` |
| **Episodic** | Past task results | Vector DB (ChromaDB / Qdrant) |
| **Semantic** | User facts / preferences | Key-value store (Redis / SQLite) |

### Adding episodic memory with ChromaDB

```bash
pip install chromadb langchain-chroma
```

```python
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings

vectorstore = Chroma(
    collection_name="agent_memory",
    embedding_function=GoogleGenerativeAIEmbeddings(model="models/text-embedding-004"),
    persist_directory="./memory_db",
)

# Save a result
vectorstore.add_texts(["User prefers dark mode on all sites"])

# Recall at start of new session
docs = vectorstore.similarity_search("display preferences", k=3)
```

---

## Phase 5 — Web Search Integration

**Goal:** Like **Perplexity**, let the agent proactively search the web before deciding what pages to visit.

### Option A: SerpAPI / Brave Search

```python
from langchain_community.tools import BraveSearch

search = BraveSearch.from_api_key(api_key=os.environ["BRAVE_API_KEY"], search_kwargs={"count": 5})
results = search.run("best Python async frameworks 2025")
```

### Option B: DuckDuckGo (free, no key)

```python
from langchain_community.tools import DuckDuckGoSearchRun

search = DuckDuckGoSearchRun()
results = search.run("Playwright vs Selenium 2025")
```

Add either as a LangChain Tool alongside your browser tools.

---

## Phase 6 — Streaming Chat UI

**Goal:** Build a real-time interface where the user watches the agent think, browse, and respond — just like ChatGPT.

### Stack recommendation

| Component | Technology |
|---|---|
| Backend API | **FastAPI** with Server-Sent Events (SSE) |
| Frontend | **Next.js** + `EventSource` API |
| Agent streaming | LangChain `StreamingStdOutCallbackHandler` |

### FastAPI SSE endpoint

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

app = FastAPI()

@app.get("/run")
async def run_agent(task: str):
    async def event_generator():
        for token in agent.stream(task):
            yield f"data: {token}\n\n"
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

---

## Phase 7 — Authentication & Session Management

**Goal:** Let the agent log into websites and maintain sessions across tasks.

### Persistent browser contexts (Playwright)

```python
# Save session after login
context = browser.new_context(storage_state="session.json")
# ...perform login...
context.storage_state(path="session.json")

# Restore session next run
context = browser.new_context(storage_state="session.json")
```

### Cookie injection

```python
context.add_cookies([{
    "name": "session_id",
    "value": "abc123",
    "domain": "example.com",
    "path": "/"
}])
```

---

## Phase 8 — Security & Sandboxing

**Goal:** Safely run the agent on untrusted tasks without compromising the host system.

### Sandboxing strategies

| Strategy | Description |
|---|---|
| **Docker container** | Run Playwright in an isolated container with no host mounts |
| **VM / Firecracker** | Full OS isolation (used by Comet, Anthropic Computer Use) |
| **Chromium flags** | `--disable-extensions --no-sandbox --incognito` |
| **Network proxy** | Route all traffic through a whitelist proxy |
| **Action allowlist** | Only allow the LLM to use pre-approved tools |

### Minimal Docker setup

```dockerfile
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "agent.py"]
```

---

## Phase 9 — Multi-Agent Architecture

**Goal:** Assign specialist sub-agents to different tasks, coordinated by a supervisor — the architecture used by **Google's DeepResearch** and complex AI workflows.

```
Supervisor Agent
   ├── Research Agent        → searches & reads pages
   ├── Action Agent          → clicks / fills forms
   ├── Summarisation Agent   → produces final answer
   └── Critic Agent          → validates outputs
```

Implement with **LangGraph** (recommended) or **CrewAI**:

```bash
pip install langgraph crewai
```

---

## Phase 10 — Observability & Evaluation

**Goal:** Know what the agent is doing, catch failures early, and measure quality.

### Tracing with LangSmith

```bash
pip install langsmith
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_API_KEY="your-langsmith-key"
```

Every agent run is automatically logged with full tool call history, token counts, and latency.

### Evaluation metrics

| Metric | What it measures |
|---|---|
| Task completion rate | Did the agent finish the task? |
| Tool call efficiency | Number of steps to complete task |
| Hallucination rate | Did it invent information not on the page? |
| Latency (p50/p95) | Time to first token, time to completion |

---

## Full Production Stack Summary

```
┌─────────────────────────────────────────────────────────┐
│  Next.js Chat UI  (streaming SSE, tool call cards)      │
├─────────────────────────────────────────────────────────┤
│  FastAPI Backend  (REST + SSE endpoints)                │
├─────────────────────────────────────────────────────────┤
│  LangGraph Supervisor  (plan → execute → critic loop)   │
├─────────────────────────────────────────────────────────┤
│  Gemini 1.5 Pro / Flash  (vision + text)                │
├─────────────────────────────────────────────────────────┤
│  Tool Layer                                             │
│    browser_tools (Playwright, screenshot, AXTree)       │
│    search_tools  (Brave / DuckDuckGo)                   │
│    memory_tools  (ChromaDB, Redis)                      │
│    code_tools    (Python REPL, file I/O)                │
├─────────────────────────────────────────────────────────┤
│  Playwright Chromium  (Docker-sandboxed)                │
├─────────────────────────────────────────────────────────┤
│  LangSmith Tracing + Evaluation                         │
└─────────────────────────────────────────────────────────┘
```

---

## Recommended Learning Resources

| Resource | Link |
|---|---|
| LangGraph docs | https://langchain-ai.github.io/langgraph/ |
| Playwright Python | https://playwright.dev/python/ |
| Gemini API docs | https://ai.google.dev/gemini-api/docs |
| Agent-E (SoM agent paper) | https://arxiv.org/abs/2407.13032 |
| WebVoyager benchmark | https://arxiv.org/abs/2401.13919 |
| Browser Use library | https://github.com/browser-use/browser-use |
| Anthropic Computer Use | https://docs.anthropic.com/en/docs/build-with-claude/computer-use |
