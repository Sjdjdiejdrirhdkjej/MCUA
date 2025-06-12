import asyncio
import pyppeteer
import logging
import os # For executable path if needed
from pyppeteer.chromium_downloader import chromium_executable, check_chromium, download_chromium

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pyppeteer configuration
# Using a specific revision can help ensure stability.
# This revision should be available for download.
# If this fails, one might need to find the latest available stable revision.
PYPPETEER_CHROMIUM_REVISION = os.environ.get("PYPPETEER_CHROMIUM_REVISION", '1263111') # From puppeteer v22.6.3
BROWSER_ARGS = [
    '--no-sandbox',
    '--disable-setuid-sandbox',
    '--disable-dev-shm-usage', # Often needed in Docker/CI environments
    '--disable-gpu', # Often not needed for headless, can cause issues
    '--headless=new', # New headless mode
    '--disable-features=site-per-process', # Mitigates some crashes with iframes
    '--disable-extensions',
    '--disable-popup-blocking',
    '--enable-automation',
    '--disable-infobars',
    '--disable-background-networking',
    '--disable-background-timer-throttling',
    '--disable-breakpad',
    '--disable-client-side-phishing-detection',
    '--disable-component-update',
    '--disable-default-apps',
    '--disable-domain-reliability',
    '--disable-features=AudioServiceOutOfProcess',
    '--disable-hang-monitor',
    '--disable-ipc-flooding-protection',
    '--disable-notifications',
    '--disable-offer-store-unmasked-wallet-cards',
    '--disable-pepper-3d',
    '--disable-print-preview',
    '--disable-prompt-on-repost',
    '--disable-renderer-backgrounding',
    '--disable-sync',
    '--disable-translate',
    '--metrics-recording-only',
    '--mute-audio',
    '--no-first-run',
    '--safebrowsing-disable-auto-update',
    '--use-mock-keychain',
]

class BrowserManager:
    _instance = None # Singleton instance

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BrowserManager, cls).__new__(cls)
            cls._instance.browser = None
            cls._instance.pages = [] # List of Page objects
            cls._instance.current_page_index = -1
            cls._instance.is_launching = False # Lock to prevent multiple launch attempts
            cls._instance.launch_lock = asyncio.Lock()

        return cls._instance

    async def ensure_chromium_downloaded(self):
        if not check_chromium(): # Changed: Removed PYPPETEER_CHROMIUM_REVISION argument
            logger.info(f"Chromium (default revision for installed pyppeteer) not found. Downloading revision {PYPPETEER_CHROMIUM_REVISION} as fallback/specific...")
            # We still use PYPPETEER_CHROMIUM_REVISION for download, as check_chromium() with no args
            # checks for *a* valid Chromium, not necessarily our specific one.
            # If default is missing, we definitely want to download our specified one.
            download_chromium() # Changed: Removed argument
            logger.info(f"Chromium download attempt for default revision complete (intended: {PYPPETEER_CHROMIUM_REVISION}).")
        else:
            logger.info(f"A Chromium revision is already available (checked via check_chromium()). Verifying specified revision {PYPPETEER_CHROMIUM_REVISION} path...")
            # Even if check_chromium() is true, we want to ensure OUR specific revision's path is used.
            # The `chromium_executable` function will give us the path for our specific revision.

        # Get executable path after ensuring download
        self.executable_path = chromium_executable(PYPPETEER_CHROMIUM_REVISION)
        if not os.path.exists(self.executable_path):
            logger.warning(f"Chromium executable for revision {PYPPETEER_CHROMIUM_REVISION} not found at {self.executable_path} after initial check/download. Attempting explicit download of default revision.")
            # Attempt download again if path doesn't exist, could be an issue with pyppeteer's check/download logic
            # or if the default check_chromium() passed but our specific revision is missing.
            download_chromium() # Changed: Removed argument
            self.executable_path = chromium_executable(PYPPETEER_CHROMIUM_REVISION) # Re-evaluate path
            if not os.path.exists(self.executable_path):
                 raise FileNotFoundError(f"Chromium executable for revision {PYPPETEER_CHROMIUM_REVISION} still not found at {self.executable_path} after fresh download attempt of default revision.")
        logger.info(f"Using Chromium executable at: {self.executable_path}")


    async def launch_browser(self):
        async with self.launch_lock: # Ensure only one coroutine attempts to launch
            if not self.browser or not self.browser.isConnected():
                if self.is_launching: # Another task is already launching
                    # Wait for the other task to finish launching
                    while self.is_launching:
                        await asyncio.sleep(0.1)
                    if self.browser and self.browser.isConnected(): # Check if previous launch was successful
                         return self.get_current_page()

                self.is_launching = True
                try:
                    logger.info("Ensuring Chromium is available...")
                    await self.ensure_chromium_downloaded()

                    logger.info(f"Launching new browser instance with executable: {self.executable_path}")
                    self.browser = await pyppeteer.launch(
                        executablePath=self.executable_path,
                        headless=True, # Always true for server-side
                        args=BROWSER_ARGS,
                        autoClose=False, # Important: keep browser open
                        # dumpio=True, # For debugging puppeteer issues
                    )
                    self.pages = [await self.browser.newPage()]
                    self.current_page_index = 0
                    await self.pages[0].setViewport({'width': 1280, 'height': 720})
                    # Add a default blank page or a specific starting page
                    await self.pages[0].goto("about:blank", {'waitUntil': 'networkidle0'})
                    logger.info("Browser launched successfully with one tab.")
                except Exception as e:
                    logger.error(f"Failed to launch browser: {e}", exc_info=True)
                    self.browser = None # Ensure browser is None if launch failed
                    self.pages = []
                    self.current_page_index = -1
                    raise # Re-raise the exception so the caller knows it failed
                finally:
                    self.is_launching = False

        return self.get_current_page()

    def get_current_page(self):
        if self.browser and self.browser.isConnected() and 0 <= self.current_page_index < len(self.pages):
            return self.pages[self.current_page_index]
        return None

    async def new_tab(self, url: str = "about:blank"):
        await self.launch_browser() # Ensure browser is running
        if not self.browser:
            raise ConnectionError("Browser is not launched or launch failed.")

        page = await self.browser.newPage()
        await page.setViewport({'width': 1280, 'height': 720})
        await page.goto(url, {'waitUntil': 'networkidle0'})
        self.pages.append(page)
        self.current_page_index = len(self.pages) - 1
        logger.info(f"Opened new tab ({self.current_page_index}). Total tabs: {len(self.pages)}")
        return page

    async def switch_tab(self, index: int):
        await self.launch_browser() # Ensures browser is running
        if not self.browser:
             return False, "Browser not available."
        if 0 <= index < len(self.pages):
            self.current_page_index = index
            logger.info(f"Switched to tab {index}.")
            return True, f"Switched to tab {index}."
        logger.warning(f"Invalid tab index {index} requested. Total tabs: {len(self.pages)}")
        return False, "Invalid tab index."

    async def go_to_url(self, url: str):
        page = await self.launch_browser() # Ensure browser & get current page
        if not page:
            logger.error("go_to_url: No active page found.")
            return False, "No active page. Browser might not be launched."

        logger.info(f"Navigating tab {self.current_page_index} to {url}...")
        try:
            # Ensure URL has a scheme
            if not url.startswith(('http://', 'https://', 'file://', 'about:')):
                url = 'http://' + url

            await page.goto(url, {'waitUntil': 'networkidle2', 'timeout': 30000})
            logger.info(f"Successfully navigated tab {self.current_page_index} to {url}.")
            return True, f"Navigated to {url}."
        except pyppeteer.errors.PageError as e: # Specific Pyppeteer page errors
            logger.error(f"PageError navigating tab {self.current_page_index} to {url}: {e}")
            return False, f"Page error navigating to {url}: {e}"
        except pyppeteer.errors.TimeoutError as e: # Specific Pyppeteer timeout errors
            logger.error(f"TimeoutError navigating tab {self.current_page_index} to {url}: {e}")
            return False, f"Timeout navigating to {url}: {e}"
        except Exception as e:
            logger.error(f"Generic error navigating tab {self.current_page_index} to {url}: {e}", exc_info=True)
            return False, f"Error navigating to {url}: {e}"

    async def take_screenshot(self) -> tuple[bytes | None, str]:
        page = self.get_current_page()
        if not page:
            logger.warning("take_screenshot: No active page to screenshot.")
            return None, "No active page to screenshot."

        logger.info(f"Taking screenshot of tab {self.current_page_index} ({page.url})...")
        try:
            screenshot_bytes = await page.screenshot({'type': 'png'}) # PNG is good for screenshots
            logger.info(f"Screenshot taken successfully for tab {self.current_page_index}.")
            return screenshot_bytes, "Screenshot taken."
        except Exception as e:
            logger.error(f"Error taking screenshot for tab {self.current_page_index}: {e}", exc_info=True)
            return None, f"Error taking screenshot: {e}"

    async def get_page_content_for_llm(self) -> str:
        """Extracts title and inner text from the current page for LLM analysis."""
        page = self.get_current_page()
        if not page:
            logger.warning("get_page_content_for_llm: No active page.")
            return "Error: No active page found in the browser."

        logger.info(f"Extracting content from tab {self.current_page_index} ({page.url}) for LLM...")
        try:
            title = await page.title()
            # Using page.content() gets the full HTML, page.evaluate for innerText is better for readable text
            text_content = await page.evaluate('() => document.body.innerText')

            if text_content is None: # innerText could be null for some pages (e.g. XML files)
                text_content = "" # Default to empty string

            # Basic cleaning: remove excessive newlines and leading/trailing whitespace
            text_content = "\n".join([line.strip() for line in text_content.split('\n') if line.strip()])
            text_content = text_content.strip()

            # Limit context size to avoid overly long strings for the LLM
            # This limit should be coordinated with what the LLM can handle / what's useful
            max_len = 10000  # Approx 2500-3000 tokens, depending on text.

            formatted_content = f"Page Title: {title}\n\nVisible Text Content (first {max_len} chars):\n{text_content[:max_len]}"
            if len(text_content) > max_len:
                formatted_content += "\n[Note: Content was truncated due to length]"

            logger.info(f"Successfully extracted content from tab {self.current_page_index}. Length: {len(text_content)}")
            return formatted_content
        except Exception as e:
            logger.error(f"Error extracting page content from tab {self.current_page_index}: {e}", exc_info=True)
            return f"Error extracting page content: {str(e)}"

    async def close_browser(self):
        logger.info("Attempting to close browser...")
        if self.browser and self.browser.isConnected():
            try:
                await self.browser.close()
                logger.info("Browser closed successfully.")
            except Exception as e:
                logger.error(f"Error closing browser: {e}", exc_info=True)
        else:
            logger.info("Browser was not running or already disconnected.")
        self.browser = None
        self.pages = []
        self.current_page_index = -1
        self.is_launching = False # Reset launch flag

# Global singleton instance of the browser manager
browser_manager_instance = BrowserManager()

# Optional: If you plan to use it with FastAPI's dependency injection
# async def get_browser_manager():
#    return browser_manager_instance
