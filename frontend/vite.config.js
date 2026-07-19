import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const vendorGroups = [
  ['vendor-react', ['react', 'react-dom']],
  ['vendor-router', ['react-router-dom']],
  ['vendor-query', ['@tanstack/react-query']],
  ['vendor-supabase', ['@supabase/supabase-js']],
  ['vendor-icons', ['lucide-react']],
  ['vendor-forms', ['react-hook-form', '@hookform/resolvers', 'zod']],
]

function manualChunks(id) {
  const normalizedId = id.replaceAll('\\', '/')
  for (const [chunkName, packages] of vendorGroups) {
    if (packages.some((name) => normalizedId.includes(`/node_modules/${name}/`))) {
      return chunkName
    }
  }
}

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks,
      },
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
