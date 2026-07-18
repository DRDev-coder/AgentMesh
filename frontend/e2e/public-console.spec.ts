import { expect, test } from '@playwright/test'

const routes = ['/', '/login', '/signup', '/docs', '/developers', '/company']

for (const route of routes) {
  test(`public route ${route} has a clean browser console`, async ({ page }) => {
    const browserErrors: string[] = []
    const failedResponses: string[] = []

    page.on('console', (message) => {
      const missingTurnstileWidget =
        message.type() === 'warning' && message.text().includes('Cannot find Widget')
      if (message.type() === 'error' || missingTurnstileWidget) {
        const source = message.location().url || 'unknown source'
        const knownTurnstileFormattingNoise =
          source.startsWith('https://challenges.cloudflare.com/') &&
          message.text().includes('font-size:0;color:transparent NaN')
        if (!knownTurnstileFormattingNoise) {
          browserErrors.push(`${source}: ${message.text()}`)
        }
      }
    })
    page.on('pageerror', (error) => browserErrors.push(error.message))
    page.on('response', (response) => {
      if (response.status() < 400) return
      const expectedTurnstileProbe =
        response.status() === 401 && response.url().startsWith('https://challenges.cloudflare.com/')
      if (!expectedTurnstileProbe) {
        failedResponses.push(`${response.status()} ${response.url()}`)
      }
    })

    const response = await page.goto(route, { waitUntil: 'domcontentloaded' })
    expect(response?.status()).toBeLessThan(400)
    await page.waitForTimeout(route === '/signup' ? 4_000 : 750)
    if (route === '/signup') {
      await page.getByRole('link', { name: 'Sign in' }).click()
      await page.waitForTimeout(500)
    }

    expect(browserErrors, `Console errors on ${route}`).toEqual([])
    expect(failedResponses, `Failed network responses on ${route}`).toEqual([])
  })
}
