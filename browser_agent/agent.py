"""
agent.py
General-purpose, high-performance browser agent.
"""

import argparse
import os
import time as _time
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

load_dotenv()

from browser_tools import BrowserController

browser = BrowserController()
browser.start()

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@tool
def open_url(url: str) -> str:
    """Open any URL in the browser. Input must be a full URL (e.g. https://google.com)."""
    return browser.open_url(url)

@tool
def click_on_text(text: str) -> str:
    """Click on a button, link, or element by its visible text. Perfect for navigation and menus."""
    return browser.click_on_text(text)

@tool
def click_by_index(index: int) -> str:
    """Click an element by its index from get_elements(). The most reliable way to interact."""
    return browser.click_by_index(index)

@tool
def type_text(selector: str, text: str) -> str:
    """Type text into an input field (CSS selector). Use get_elements() to find the right field."""
    return browser.type_text(selector, text)

@tool
def press_key(key: str) -> str:
    """Press a keyboard key (e.g. 'Enter', 'Escape', 'ArrowDown')."""
    return browser.press_key(key)

@tool
def get_elements(ignored: str = "") -> str:
    """Scan the current page for all interactive elements and return them with indices [0, 1, 2...]."""
    return browser.get_elements()

@tool
def scroll(direction: str) -> str:
    """Scroll the page 'up' or 'down'."""
    return browser.scroll(direction)

@tool
def wait_ms(ms: int) -> str:
    """Wait for a number of milliseconds (e.g. 2000 = 2 seconds) for content to load."""
    return browser.wait_ms(ms)

@tool
def read_text(ignored: str = "") -> str:
    """Read the main text content of the current page."""
    return browser.read_text()

@tool
def take_screenshot(filename: str) -> str:
    """Save a snapshot of the current view to the 'screenshots/' folder for verification."""
    return browser.take_screenshot(filename)

@tool
def close_browser(ignored: str = "") -> str:
    """Finished the task? Call this to close the browser session."""
    browser.close()
    return "Browser closed."

tools = [
    open_url, click_on_text, click_by_index, type_text, 
    press_key, get_elements, scroll, wait_ms, 
    read_text, take_screenshot, close_browser
]

# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------
api_key = os.environ.get("GOOGLE_API_KEY")
llm = ChatGoogleGenerativeAI(
    model="gemini-flash-latest",
    temperature=0,
    google_api_key=api_key,
)

agent = create_react_agent(llm, tools)

# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

def run_agent_with_retry(task: str, max_retries: int = 5):
    prompt = (
        f"You are a lightning-fast, highly capable browser agent. Task: {task}\n\n"
        "CORE SUCCESS PRINCIPLES:\n"
        "1. DIRECT ACTION: Go straight to the URL. Use search bars or direct navigation to save time.\n"
        "2. PRECISION TOOLS: Use get_elements() to see exactly what's on screen. Interact via click_by_index() for flawless results.\n"
        "3. GENERALIST: You handle all websites perfectly—news, social media, video, search, or tools.\n"
        "4. ADAPTABILITY: If you encounter a popup (cookies, ads, logins), get_elements() and click it away immediately.\n"
        "5. COMPLETION: Once you verified success, call close_browser()."
    )

    print(f"\n🚀  Executing: {task}")

    for attempt in range(1, max_retries + 1):
        try:
            for step in agent.stream({"messages": [("human", prompt)]}, stream_mode="values"):
                msg = step["messages"][-1]
                msg.pretty_print()
            return 
        except Exception as e:
            err = str(e)
            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                wait_time = 5 * attempt
                print(f"\n⚠️  Quota Limit (Attempt {attempt}/{max_retries}). Retrying in {wait_time}s...")
                _time.sleep(wait_time)
            else:
                print(f"❌ Execution Error: {e}")
                return

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    args = parser.parse_args()

    try:
        run_agent_with_retry(args.query)
    finally:
        browser.close()
