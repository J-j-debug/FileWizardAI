from playwright.sync_api import sync_playwright, expect

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    page.goto("http://localhost:4200")

    # Locate the select dropdown by its label
    select_locator = page.locator("mat-form-field.collection-select")

    # Assert that the select is visible
    expect(select_locator).to_be_visible()

    # Click to open the dropdown
    select_locator.click()

    # Select the "Recherche Avancée (Unstructured)" option
    page.get_by_role("option", name="Recherche Avancée (Unstructured)").click()

    # Assert that the value has changed
    expect(select_locator).to_contain_text("Recherche Avancée (Unstructured)")

    # Take a screenshot
    page.screenshot(path="jules-scratch/verification/verification.png")

    browser.close()

with sync_playwright() as playwright:
    run(playwright)
