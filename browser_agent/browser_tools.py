"""
browser_tools.py
BrowserController: wraps Playwright Chromium.
Runs Playwright in a dedicated background thread to avoid greenlet
conflicts when called from LangGraph's worker threads.
"""

import os
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
                    elif cmd == "type_text":
                        print(f"[BrowserController] Typing '{args[1]}' into: {args[0]}")
                        page.fill(args[0], args[1], timeout=10000)
                        page.wait_for_timeout(1000)
                        result_q.put(("ok", f"Typed into {args[0]}"))
                    elif cmd == "press_key":
                        print(f"[BrowserController] Pressing key: {args[0]}")
                        page.keyboard.press(args[0])
                        page.wait_for_timeout(1000)
                        result_q.put(("ok", f"Pressed {args[0]}"))
                    elif cmd == "scroll":
                        direction = args[0] # 'up' or 'down'
                        print(f"[BrowserController] Scrolling {direction}...")
                        if direction == "down":
                            page.mouse.wheel(0, 600)
                        else:
                            page.mouse.wheel(0, -600)
                        page.wait_for_timeout(1000)
                        result_q.put(("ok", f"Scrolled {direction}"))
                    elif cmd == "take_screenshot":
                        filename = args[0]
                        print(f"[BrowserController] Taking screenshot: {filename}")
                        os.makedirs("screenshots", exist_ok=True)
                        filepath = os.path.join("screenshots", filename)
                        page.screenshot(path=filepath)
                        result_q.put(("ok", f"Screenshot saved to {filepath}"))
                    elif cmd == "get_elements":
                        print("[BrowserController] Listing interactive elements...")
                        elements = page.evaluate("""() => {
                            const results = [];
                            const clickable = Array.from(document.querySelectorAll('button, a, input, [role="button"], [contenteditable="true"]'));
                            
                            clickable.forEach((el, index) => {
                                const rect = el.getBoundingClientRect();
                                if (rect.width > 0 && rect.height > 0 && rect.top >= 0 && rect.left >= 0) {
                                    const text = (el.innerText || el.value || el.placeholder || el.getAttribute('aria-label') || '').trim();
                                    const tag = el.tagName.toLowerCase();
                                    const id = el.id ? '#' + el.id : '';
                                    const type = el.getAttribute('type') || '';
                                    results.push(`[${index}] ${tag}${id}${type ? '[type="'+type+'"]' : ''} - "${text.substring(0,30)}"`);
                                }
                            });
                            return results.slice(0, 60);
                        }""")
                        result_q.put(("ok", "\\n".join(elements)))
                    elif cmd == "click_on_text":
                        text = args[0]
                        print(f"[BrowserController] Clicking on text: {text}")
                        # Try to find an element with that text (case-insensitive)
                        try:
                            page.get_by_text(text, exact=False).first.click(timeout=5000)
                            page.wait_for_timeout(1000)
                            result_q.put(("ok", f"Clicked on text: {text}"))
                        except Exception as e:
                            result_q.put(("err", f"Could not find or click text '{text}': {str(e)}"))
                    elif cmd == "click_by_index":
                        index = int(args[0])
                        print(f"[BrowserController] Clicking by index: {index}")
                        page.evaluate(f"""(idx) => {{
                            const clickable = Array.from(document.querySelectorAll('button, a, input, [role="button"], [contenteditable="true"]'));
                            const el = clickable[idx];
                            if (el) {{
                                el.scrollIntoView();
                                el.click();
                            }} else {{
                                throw new Error("Index " + idx + " not found");
                            }}
                        }}""", index)
                        page.wait_for_timeout(1000)
                        result_q.put(("ok", f"Clicked element at index {index}"))
                    elif cmd == "wait_for_selector":
                        selector = args[0]
                        print(f"[BrowserController] Waiting for selector: {selector}")
                        page.wait_for_selector(selector, timeout=10000)
                        result_q.put(("ok", f"Selector {selector} is now visible"))
                    elif cmd == "wait_ms":
                        ms = int(args[0])
                        print(f"[BrowserController] Waiting for {ms}ms...")
                        page.wait_for_timeout(ms)
                        result_q.put(("ok", f"Waited {ms}ms"))
                    elif cmd == "save_to_file":
                        filename, content = args[0], args[1]
                        print(f"[BrowserController] Saving content to: {filename}")
                        with open(filename, "w") as f:
                            f.write(content)
                        result_q.put(("ok", f"Data saved to {filename}"))
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

    def type_text(self, selector: str, text: str) -> str:
        return self._dispatch("type_text", selector, text)

    def press_key(self, key: str) -> str:
        return self._dispatch("press_key", key)

    def scroll(self, direction: str) -> str:
        return self._dispatch("scroll", direction)

    def take_screenshot(self, filename: str) -> str:
        return self._dispatch("take_screenshot", filename)

    def get_elements(self) -> str:
        return self._dispatch("get_elements")

    def click_on_text(self, text: str) -> str:
        return self._dispatch("click_on_text", text)

    def click_by_index(self, index: int) -> str:
        return self._dispatch("click_by_index", str(index))

    def wait_for_selector(self, selector: str) -> str:
        return self._dispatch("wait_for_selector", selector)

    def wait_ms(self, ms: int) -> str:
        return self._dispatch("wait_ms", str(ms))

    def save_to_file(self, filename: str, content: str) -> str:
        return self._dispatch("save_to_file", filename, content)

    def close(self):
        if self._thread.is_alive():
            try:
                self._dispatch("STOP")
            except Exception:
                pass
