import { test, expect } from '@playwright/test';

test.describe('Application E2E Tests', () => {
  test('should run basic and research hub checks', async ({ page }) => {
    // Navigate to the app
    await page.goto('http://localhost:4200/');

    // --- Part 1: Basic Search View Check ---
    console.log('Checking Basic Search view...');
    // Check if the "File Structure Manager" is visible by default
    await expect(page.locator('h2:has-text("File Structure Manager")')).toBeVisible({ timeout: 10000 });
    console.log('File Structure Manager is visible.');

    // --- Part 2: Research Hub Functionality ---
    console.log('Switching to Research Hub...');
    // Click the button to switch to the Research Hub view
    await page.locator('button:has-text("Hub de Recherche")').click({ force: true });
    await page.waitForTimeout(1000); // Wait for UI to update

    // Check if the "My Notebooks" title is visible
    console.log('Checking for "My Notebooks" title...');
    await expect(page.locator('mat-card-title:has-text("My Notebooks")')).toBeVisible();
    console.log('Research Hub is visible.');

    // Create a new notebook
    const notebookName = `Test Notebook ${Date.now()}`;
    console.log(`Creating notebook: ${notebookName}`);
    await page.fill('input[name="name"]', notebookName);
    await page.fill('textarea[name="description"]', 'A notebook for E2E testing.');
    await page.locator('button:has-text("Create")').click();

    // Wait for the notebook to appear in the list and check for its name
    await expect(page.locator(`div:has-text("${notebookName}")`).first()).toBeVisible({ timeout: 5000 });
    console.log('Notebook created successfully.');

    // Click on the newly created notebook to select it
    const notebookLocator = page.locator('mat-list-item', { hasText: notebookName });
    await notebookLocator.waitFor({ state: 'visible', timeout: 5000 });
    await notebookLocator.click();
    console.log('Navigating into the notebook...');

    // Inside the notebook view, wait for and check for the "Notebook Files" title
    const titleLocator = page.locator('mat-card-title:has-text("Notebook Files")');
    await titleLocator.waitFor({ state: 'visible', timeout: 10000 });
    await expect(titleLocator).toBeVisible();
    console.log('Entered notebook view.');

    // Simulate adding a file via prompt
    const filePath = '/app/test_document.txt';
    page.once('dialog', async dialog => {
      console.log(`Dialog opened: ${dialog.message()}`);
      await dialog.accept(filePath);
      console.log('Accepted dialog with file path.');
    });

    // Click the "Add Files" button
    await page.locator('button:has-text("Add Files")').click();

    // Check if the file appears in the list
    const fileLocator = page.locator('mat-list-item', { hasText: filePath });
    await expect(fileLocator).toBeVisible();
    console.log('First file added successfully.');

    // --- Part 3: Test the bug fix (adding a second file) ---
    console.log('Attempting to add a second file...');

    // Re-register the dialog handler for the second file addition
    page.once('dialog', async dialog => {
      console.log(`Dialog opened: ${dialog.message()}`);
      const secondFilePath = '/app/another_doc.txt';
      await dialog.accept(secondFilePath);
      console.log('Accepted dialog with second file path.');
    });

    // Click "Add Files" again
    await page.locator('button:has-text("Add Files")').click();

    // Check if the second file appears in the list
    const secondFileLocator = page.locator('mat-list-item', { hasText: '/app/another_doc.txt' });
    await expect(secondFileLocator).toBeVisible();
    console.log('Successfully added a second file. Bug is fixed.');

    // --- Final Step ---
    console.log('E2E test completed successfully.');
  });
});
