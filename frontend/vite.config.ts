import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  server: {
    port: 5173,
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // Separate chunk for Leaflet and map-related libraries
          leaflet: ['leaflet', 'react-leaflet', 'leaflet.markercluster', 'react-leaflet-cluster'],
          // Separate chunk for Radix UI components
          'radix-ui': [
            '@radix-ui/react-dialog',
            '@radix-ui/react-dropdown-menu',
            '@radix-ui/react-scroll-area',
            '@radix-ui/react-select',
            '@radix-ui/react-separator',
            '@radix-ui/react-slot',
            '@radix-ui/react-tabs',
            '@radix-ui/react-tooltip'
          ],
          // Separate chunk for React Router
          router: ['react-router-dom']
        }
      }
    },
    // Increase chunk size warning limit slightly
    chunkSizeWarningLimit: 600
  }
})
