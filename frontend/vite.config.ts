import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';


const backendPort = process.env.VITE_BACKEND_PORT || '8000';


export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: `http://127.0.0.1:${backendPort}`,
        changeOrigin: true,
      },
    },
  },
  build: {
    // Let Vite own vendor chunking so React/Ant Design stay in a safe module order.
    // Route-level lazy loading still keeps the heavy pages split without introducing cycles.
  },
});
