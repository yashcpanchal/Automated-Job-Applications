from fastapi import APIRouter
from dependencies.database import DatabaseDependency
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
import asyncio

router = APIRouter (
    prefix="/apply",
    tags=["Apply using agent"]
)


# Update the data dictionaries with pydantic schemas
# Change to non-headless browser for debugging purposes
@router.post("/")
async def apply_to_job(db: DatabaseDependency, data: dict):
    url = data.get("url")
    print(f"Url is {url}")
    async with async_playwright() as p:
        print("Launching function")
        browser = await p.chromium.launch()
        
        print("Opening browser")
        page = await browser.new_page()
        
        print("Applying stealth")
        await stealth_async(page)
        
        print("Navigating to url")

        try:
            await page.goto(url, wait_until="domcontentloaded")
            await page.wait_for_timeout(1000)
            await page.screenshot(path="test.png")
            print("Getting page title")
            title = await page.title()
        except Exception as e:
            print(f"Exception caught when waiting for dom content to load: {e}")
        finally:
            await browser.close()
        return {"title": title}
    return {"message": "Something went wrong."}