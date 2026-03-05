# 🤖 Browser Agent (webRover)

A lightning-fast, autonomous browser agent powered by Gemini and Playwright. It can navigate websites, search for information, interact with elements, and even play media autonomously.

## 🚀 Features

- **Lightning-Fast Interaction:** Uses optimized text-based and index-based clicking to bypass slow CSS selectors.
- **Autonomous Planning:** Generates a to-do list for every task before execution.
- **Visual Awareness:** Can take screenshots for verification and debugging.
- **General Purpose:** Works on any website—YouTube, Wikipedia, Google, News, etc.
- **Secure:** API keys are managed through environment variables.
- **Robust:** Includes built-in rate-limit handling and retries.

## 🛠️ Setup

### 1. Prerequisites
- [Python 3.11+](https://www.python.org/)
- [uv](https://github.com/astral-sh/uv) (recommended) or `pip`

### 2. Installation
Clone the repository and install dependencies:
```bash
# Install dependencies using uv
uv sync

# Install Playwright browsers
uv run playwright install chromium
```

### 3. Configuration
Create a `.env` file in the `browser_agent/` directory:
```bash
GOOGLE_API_KEY=your_gemini_api_key_here
```
> [!NOTE]
> The project already includes a `.gitignore` to ensure your `.env` and `.venv` are never committed.

## 📖 Usage

Run the agent by providing a task as a command-line argument:

### General Search
```bash
uv run agent.py "Go to wikipedia.org, find today's featured article, and tell me the title."
```

### Media / YouTube
```bash
uv run agent.py "Open YouTube and play a Bollywood hindi song."
```

### Data Extraction
```bash
uv run agent.py "Go to news.ycombinator.com and save the top 5 story titles to 'news.txt'."
```

## 📂 Project Structure
- `agent.py`: The main entry point and LLM logic.
- `browser_tools.py`: Playwright wrapper and browser interaction tools.
- `screenshots/`: Folder where visual snapshots are saved.
- `.env`: (Local only) Secure API key storage.
