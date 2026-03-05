"""
agent.py
AI-powered browser agent: Gemini LLM + LangGraph ReAct + Playwright.

Usage:
    export GOOGLE_API_KEY="AIzaSyB1ign_npgd52HpmXPFshyVAiZ7BB_LbPg"
    python agent.py
"""

import os
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

# Load environment variables from .env file
load_dotenv()

from browser_tools import BrowserController

# ---------------------------------------------------------------------------
# Initialise browser
# ---------------------------------------------------------------------------
browser = BrowserController()
browser.start()

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@tool
def open_url(url: str) -> str:
    """Open a URL in the browser. Input must be a full URL starting with http:// or https://."""
    return browser.open_url(url)


@tool
def click(selector: str) -> str:
    """Click an element on the current page using a CSS selector."""
    return browser.click(selector)


@tool
def read_text(ignored: str = "") -> str:
    """Read and return all visible text from the current page body (up to 8000 chars). Input is ignored."""
    return browser.read_text()


@tool
def close_browser(ignored: str = "") -> str:
    """Close the browser. Call this as the final step when done."""
    browser.close()
    return "Browser closed."


tools = [open_url, click, read_text, close_browser]

# ---------------------------------------------------------------------------
# Gemini
# ---------------------------------------------------------------------------
api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    raise EnvironmentError("GOOGLE_API_KEY not set. Run: export GOOGLE_API_KEY='your-key'")

llm = ChatGoogleGenerativeAI(
    model="gemini-flash-latest",
    temperature=0,
    google_api_key=api_key,
)

# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------
agent = create_react_agent(llm, tools)

# ---------------------------------------------------------------------------
# Task — Search Google for Mumbai-Pune distance, then read an article
# ---------------------------------------------------------------------------
TASK = (
    "You are a browser agent. Complete these steps in order:\n"
    "1. Open https://duckduckgo.com/?q=distance+between+mumbai+and+pune\n"
    "2. Read the page text and find the exact distance between Mumbai and Pune. State it clearly.\n"
    "3. Find and click on the first organic result link on the page "
    "(use the CSS selector 'a[data-testid=\"result-title-a\"]' or similar to click the first result).\n"
    "4. Read the text of that article and give me a 2-sentence summary of what it says "
    "about the Mumbai-Pune route.\n"
    "5. Close the browser.\n"
    "Be concise and report each finding step by step."
)

print("\n" + "=" * 60)
print("🤖  Browser Agent")
print(f"📋  Task: {TASK}")
print("=" * 60 + "\n")

# ---------------------------------------------------------------------------
# Run with retry on 429 rate-limit errors
# ---------------------------------------------------------------------------
import time as _time

def run_agent_with_retry(max_retries: int = 5):
    for attempt in range(1, max_retries + 1):
        try:
            for step in agent.stream(
                {"messages": [("human", TASK)]},
                stream_mode="values",
            ):
                msg = step["messages"][-1]
                msg.pretty_print()
                _time.sleep(1)
            return  # success
        except Exception as e:
            err = str(e)
            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                wait = 15 * attempt
                print(f"\n⚠️  Rate limit hit (attempt {attempt}/{max_retries}). Waiting {wait}s...")
                _time.sleep(wait)
            else:
                raise  # non-rate-limit error — re-raise immediately

try:
    run_agent_with_retry()
    print("\n" + "=" * 60)
    print("✅  Agent finished.")
    print("=" * 60)
finally:
    browser.close()
