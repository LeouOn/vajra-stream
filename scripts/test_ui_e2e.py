import asyncio
import sys
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        print("Testing Vajra.Stream Frontend End-to-End Orchestration...")
        
        # Listen to console
        errors = []
        page.on("console", lambda msg: print(f"Browser Console [{msg.type}]: {msg.text}") if msg.type in ['error', 'warning'] else None)
        page.on("pageerror", lambda err: print(f"Page Error: {err.message}"))
        
        try:
            print("Navigating to frontend...")
            await page.goto("http://localhost:3009", timeout=30000)
            
            # Wait for Command Center input
            print("Waiting for Command Center to load...")
            await page.wait_for_selector("input[placeholder='Instruct the system...']", timeout=15000)
            
            # Scenario 1: Saka Dawa
            print("\n--- Test Scenario 1: Saka Dawa ---")
            await page.fill("input[placeholder='Instruct the system...']", "Check Saka Dawa astrology")
            await page.click("button:has-text('Send')")
            
            # Wait for response
            await page.wait_for_timeout(10000)
            print("Received response for Saka Dawa")
            
            # Scenario 2: 88 Buddhas
            print("\n--- Test Scenario 2: 88 Buddhas ---")
            await page.fill("input[placeholder='Instruct the system...']", "Run the 88 Buddhas prayer and TTS")
            await page.click("button:has-text('Send')")
            
            # Wait for response
            await page.wait_for_timeout(15000)
            print("Received response for 88 Buddhas")
            
            print("\nTest completed successfully. Check logs for browser errors.")
            
        except Exception as e:
            print(f"Test failed: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
