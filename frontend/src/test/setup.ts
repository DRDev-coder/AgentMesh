import '@testing-library/jest-dom/vitest'

Object.defineProperty(window.navigator, 'clipboard', {
  configurable: true,
  value: { writeText: async () => undefined },
})
