import { test, expect } from '@playwright/test';

test('Research Hub Navigation and Initial State', async ({ page }) => {
  try {
    // Navigate to the application
    await page.goto('http://localhost:4200');

    // DEBUG: Log the page content to see what's rendering
    const content = await page.content();
    console.log(content);

    // Find and click the 'Hub de Recherche' tab link
    const researchHubLink = page.locator('a:has-text("Hub de Recherche")');
    await researchHubLink.click({ timeout: 10000 }); // Reduce timeout for faster failure

    // Verify that the 'Research Hub' component is visible
    await expect(page.locator('app-research-hub')).toBeVisible();

    // Verify that the 'Basic Search' component is not visible
    await expect(page.locator('app-search-files')).toHaveCount(0);

    // Verify that the notebook list is displayed
    await expect(page.locator('h2:has-text("Mes Cahiers de Recherche")')).toBeVisible();

    // Take a screenshot of the final state
    await page.screenshot({ path: '/home/jules/verification/final_view.png' });
  } catch (error) {
    // Take a screenshot on failure
    await page.screenshot({ path: '/home/jules/verification/failure_screenshot.png' });
    throw error;
  }
});
