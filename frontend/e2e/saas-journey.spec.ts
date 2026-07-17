import path from 'node:path'
import { expect, test } from '@playwright/test'

test('onboarding to published knowledge, decision trace, and usage', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Configure your first AgentMesh workspace.' })).toBeVisible()

  await page.getByLabel('Company name').fill(`Journey ${Date.now()}`)
  await page.getByRole('button', { name: /create company and test key/i }).click()
  await expect(page.getByText('Support is ready to configure.')).toBeVisible()
  await expect(page.locator('.secret-reveal code')).toContainText('am_test_')

  await page.getByRole('button', { name: /continue to knowledge/i }).click()
  await page.locator('input[type="file"]').setInputFiles(
    path.join(process.cwd(), 'e2e', 'fixtures', 'returns.md'),
  )
  await page.getByRole('button', { name: /upload document/i }).click()
  await expect(page.getByText('READY FOR REVIEW')).toBeVisible()
  await page.getByRole('button', { name: /publish release/i }).click()
  await expect(page.getByText('PUBLISHED')).toBeVisible()

  await page.getByRole('link', { name: /playground/i }).click()
  await page.getByLabel('Customer question').fill('How long can I return an unopened product?')
  await page.getByRole('button', { name: /run decision/i }).click()
  await expect(page.getByText(/unit$/)).toBeVisible({ timeout: 30_000 })
  await expect(page.locator('.decision-evidence')).toContainText('Evidence')

  await page.getByRole('link', { name: /decisions/i }).click()
  await expect(page.getByRole('heading', { name: 'Decision records' })).toBeVisible()
  await expect(page.locator('.decision-list button')).toHaveCount(1)

  await page.getByRole('link', { name: /usage.*billing/i }).click()
  await expect(page.getByRole('heading', { name: '1 completed decisions' })).toBeVisible()
  await expect(page.getByText(/stripe invoice projections update asynchronously/i)).toBeVisible()
})
