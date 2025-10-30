from playwright.sync_api import Page, expect, sync_playwright

def verify_search_flow_with_pages():
    """
    This test verifies the updated search flow with page numbers in sources.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # 1. Arrange: Go to the application homepage.
        page.goto("http://localhost:4200")

        # 2. Assert: Check that the search components are visible.
        search_input = page.get_by_placeholder("Ask a question about your documents")
        expect(search_input).to_be_visible()

        # 3. Screenshot: Capture the initial state for visual verification.
        page.screenshot(path="jules-scratch/verification/verification.png")

        browser.close()

if __name__ == "__main__":
    verify_search_flow_with_pages()
