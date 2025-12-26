# backend/scraper.py
import requests
from bs4 import BeautifulSoup, NavigableString, Tag
import re

HEADERS = {
    "User-Agent": "ai-quiz-generator/1.0 (https://example.com) Python requests"
}

def _clean_paragraph(p: Tag) -> str:
    """Return cleaned text from a <p> tag, stripping sup, reference links, and extra whitespace."""
    # remove sup and reference anchors
    for sup in p.find_all("sup"):
        sup.decompose()
    for a in p.find_all("a", class_="mw-selflink"):
        a.unwrap()
    text = p.get_text(separator=" ", strip=True)
    # collapse multiple spaces/newlines
    text = re.sub(r"\s+", " ", text)
    return text

def scrape_wikipedia(url: str, max_paragraphs: int = None) -> tuple[str, str]:
    """
    Scrape a Wikipedia article and return (title, cleaned_text).
    max_paragraphs: optionally limit number of paragraphs (helpful for very long pages).
    """
    if not url.startswith("http"):
        raise ValueError("Please supply a full URL (including http/https).")

    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # Title
    title_tag = soup.find("h1", id="firstHeading")
    title = title_tag.get_text(strip=True) if title_tag else ""

    # Main content block
    content_div = soup.find(id="mw-content-text")
    if not content_div:
        # fallback: try article tag
        content_div = soup.find("article")

    if not content_div:
        raise RuntimeError("Couldn't find main content on the page.")

    # remove tables, infoboxes, navboxes, and other non-paragraph content
    for selector in ["table", "style", "script", "noscript", "sup", ".reference", ".toc", ".thumb", ".infobox"]:
        for node in content_div.select(selector):
            node.decompose()

    # collect paragraph texts
    paragraphs = []
    for p in content_div.find_all("p"):
        cleaned = _clean_paragraph(p)
        if cleaned:
            paragraphs.append(cleaned)
            if max_paragraphs and len(paragraphs) >= max_paragraphs:
                break

    # if no paragraphs found, try to collect text from divs
    if not paragraphs:
        texts = [t.get_text(separator=" ", strip=True) for t in content_div.find_all(["div", "span"])]
        joined = " ".join([re.sub(r"\s+", " ", t) for t in texts if t])
        return title, joined[:10000]  # limit length

    full_text = "\n\n".join(paragraphs)
    return title, full_text[:20000]  # return at most 20k chars (adjustable)
    

if __name__ == "__main__":
    # quick local test: change this URL if you want a different article
    test_url = "https://en.wikipedia.org/wiki/Python_(programming_language)"
    print("Testing scrape for:", test_url)
    t, content = scrape_wikipedia(test_url, max_paragraphs=10)
    print("TITLE:", t)
    print("--- SAMPLE ---")
    print(content[:1000])  # print first 1000 chars
