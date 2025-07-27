# from playwright.async_api import async_playwright
# from playwright_stealth import stealth_async

# class PlaywrightManager:
#     """
#     An asynchronous context manager for managing a Playwright browser instance.
#     """
#     async def __aenter__(self):
#         """
#         Called when entering the 'async with' block.
#         Initializes Playwright, launches a browser, and returns a new page.
#         """
#         print("--- LAUNCHING PLAYWRIGHT BROWSER ---")
#         self.playwright = await async_playwright().start()
#         self.browser = await self.playwright.chromium.launch(headless=True)
#         # self.page = await self.browser.new_page()
        
#         # Apply stealth measures to make the browser look more like a real user
#         await stealth_async(self.page)
        
#         return self.page

#     async def __aexit__(self, exc_type, exc_val, exc_tb):
#         """
#         Called when exiting the 'async with' block.
#         Ensures the browser and Playwright instances are closed.
#         """
#         print("--- CLOSING PLAYWRIGHT BROWSER ---")
#         if hasattr(self, 'page') and self.page:
#             await self.page.close()
#         if hasattr(self, 'browser') and self.browser:
#             await self.browser.close()
#         if hasattr(self, 'playwright') and self.playwright:
#             await self.playwright.stop()

from playwright.async_api import async_playwright

class PlaywrightManager:
    """
    Asynchronous context manager for initializing and tearing down a Playwright browser instance.
    This ensures that the browser is properly launched and closed.
    """
    async def __aenter__(self):
        """Initializes the Playwright browser."""
        print("--- LAUNCHING PLAYWRIGHT BROWSER ---")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        # Yield the browser instance so it can be used to create contexts/pages
        return self.browser

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Closes the Playwright browser."""
        print("--- CLOSING PLAYWRIGHT BROWSER ---")
        if hasattr(self, 'browser'):
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()