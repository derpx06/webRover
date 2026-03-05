"""
browser_tools.py
BrowserController: wraps Playwright Chromium.
Runs Playwright in a dedicated background thread to avoid greenlet
conflicts when called from LangGraph's worker threads.
"""

import queue
import threading
from playwright.sync_api import sync_playwright

MAX_TEXT_LENGTH = 8000


class BrowserController:
    """
    Thread-safe Playwright wrapper.
    All Playwright calls are dispatched to a single dedicated thread
    via a command queue, so the sync API stays on one greenlet.
    """

    def __init__(self):
        self._cmd_q: queue.Queue = queue.Queue()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)

    def _run_loop(self):
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=False)
            page = browser.new_page()
            # Look like a real browser to avoid bot-detection
            page.set_extra_http_headers({
                "Accept-Language": "en-US,en;q=0.9",
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            })
            print("[BrowserController] Browser started.")
            while True:
                cmd, args, result_q = self._cmd_q.get()
                if cmd == "STOP":
                    browser.close()
                    print("[BrowserController] Browser closed.")
                    result_q.put(("ok", "Browser closed."))
                    break
                try:
                    if cmd == "open_url":
                        print(f"[BrowserController] Navigating to: {args[0]}")
                        # 'load' is more robust than 'networkidle' for many sites
                        page.goto(args[0], wait_until="load", timeout=60000)
                        page.wait_for_timeout(2000)  # extra settle time
                        result_q.put(("ok", f"Navigated to {args[0]}"))
                    elif cmd == "click":
                        print(f"[BrowserController] Clicking: {args[0]}")
                        page.click(args[0], timeout=10000)
                        page.wait_for_timeout(1000)
                        result_q.put(("ok", f"Clicked: {args[0]}"))
                    elif cmd == "read_text":
                        print("[BrowserController] Reading text...")
                        text = page.inner_text("body")
                        if len(text) > MAX_TEXT_LENGTH:
                            text = text[:MAX_TEXT_LENGTH] + "\n...[truncated]"
                        result_q.put(("ok", text))
                    else:
                        result_q.put(("err", f"Unknown command: {cmd}"))
                except Exception as e:
                    result_q.put(("err", str(e)))

    def _dispatch(self, cmd: str, *args) -> str:
        result_q: queue.Queue = queue.Queue()
        self._cmd_q.put((cmd, args, result_q))
        status, value = result_q.get(timeout=90)
        if status == "err":
            return f"Error: {value}"
        return value

    def start(self):
        self._thread.start()
        import time; time.sleep(1.5)

    def open_url(self, url: str) -> str:
        return self._dispatch("open_url", url)

    def click(self, selector: str) -> str:
        return self._dispatch("click", selector)

    def read_text(self) -> str:
        return self._dispatch("read_text")

    def close(self):
        if self._thread.is_alive():
            try:
                self._dispatch("STOP")
            except Exception:
                pass
