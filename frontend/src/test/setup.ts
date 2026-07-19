import '@testing-library/jest-dom/vitest'

Object.defineProperty(window.navigator, 'clipboard', {
  configurable: true,
  value: { writeText: async () => undefined },
})

Object.defineProperty(globalThis, 'IntersectionObserver', {
  configurable: true,
  value: class IntersectionObserverMock {
    observe() {}
    unobserve() {}
    disconnect() {}
  },
})
