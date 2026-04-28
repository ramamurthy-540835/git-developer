import asyncio
import logging
from playwright.async_api import async_playwright, TimeoutError
import re

logging.basicConfig(level=logging.INFO)

async def read_app_url(url: str) -> dict:
    """
    Opens the app URL with Playwright, extracts visible page content, and returns it.
    """
    logging.info(f"Attempting to read URL: {url}")
    browser = None
    p = None
    try:
        p = await async_playwright().start()
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Increased timeout to 60s for potentially slow-loading pages
        await page.goto(url, wait_until='networkidle', timeout=60000)
        current_url = page.url
        page_title = await page.title()

        # Extract visible headings
        headings_elements = await page.locator('h1, h2, h3, h4, h5, h6').all()
        headings = [await el.text_content() for el in headings_elements if await el.is_visible()]
        headings = [h.strip() for h in headings if h.strip()]
        headings = list(dict.fromkeys(headings)) # Remove duplicates

        # Extract visible button labels
        buttons_elements = await page.locator('button, input[type="button"], input[type="submit"], a[role="button"], a[class*="button"]').all()
        buttons = []
        for el in buttons_elements:
            if await el.is_visible():
                text = await el.text_content()
                if not text: # For input buttons, get value attribute
                    text = await el.get_attribute('value')
                if text and text.strip():
                    buttons.append(text.strip())
        buttons = list(dict.fromkeys(buttons)) # Remove duplicates while preserving order

        # Extract visible card titles (heuristic: div with a prominent heading)
        # This is a heuristic and might need refinement. Looking for divs that contain h2/h3 and are visible.
        cards = []
        card_elements = await page.locator('div:has(h2), div:has(h3)').all()
        for el in card_elements:
            if await el.is_visible():
                # Try to get a concise title from within the potential card element
                h_title_el = await el.locator('h2, h3').first.all_text_contents()
                if h_title_el and h_title_el[0].strip():
                    cards.append(h_title_el[0].strip())
        cards = list(dict.fromkeys(cards)) # Remove duplicates

        # Extract visible paragraph text
        paragraphs_elements = await page.locator('p').all()
        paragraphs = [await el.text_content() for el in paragraphs_elements if await el.is_visible()]
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        # Extract visible table headers
        tables = []
        table_elements = await page.locator('table').all()
        for table_el in table_elements:
            if await table_el.is_visible():
                headers = []
                th_elements = await table_el.locator('th').all()
                for th_el in th_elements:
                    header_text = await th_el.text_content()
                    if header_text and header_text.strip():
                        headers.append(header_text.strip())
                if headers:
                    # Also try to find a caption if available
                    caption_el = await table_el.locator('caption').first.all_text_contents()
                    caption = caption_el[0].strip() if caption_el else None
                    tables.append({"headers": headers, "caption": caption})

        # Extract raw visible text content, limited to 8000 chars
        raw_text_content = await page.main_frame.text_content()
        raw_text = raw_text_content[:8000] if raw_text_content else ""
        raw_text = raw_text.strip()
        # Remove excessive whitespace/newlines
        raw_text = re.sub(r'\n\s*\n', '\n', raw_text)
        raw_text = re.sub(r' {2,}', ' ', raw_text)


        return {
            "title": page_title,
            "url": current_url,
            "headings": headings,
            "buttons": buttons,
            "cards": cards,
            "paragraphs": paragraphs,
            "tables": tables,
            "raw_text": raw_text
        }

    except TimeoutError:
        logging.error(f"Timeout while reading URL: {url}")
        return {
            "title": "Error: Timeout",
            "url": url,
            "headings": [], "buttons": [], "cards": [], "paragraphs": [], "tables": [],
            "raw_text": "Could not access page content within the allotted time."
        }
    except Exception as e:
        logging.error(f"Failed to read URL {url}: {e}", exc_info=True)
        return {
            "title": f"Error reading page: {type(e).__name__}",
            "url": url,
            "headings": [], "buttons": [], "cards": [], "paragraphs": [], "tables": [],
            "raw_text": f"Error: {e}"
        }
    finally:
        if browser:
            await browser.close()
        if p:
            await p.stop()
