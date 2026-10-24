import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          three: ['three'],
          motion: ['framer-motion'],
        },
      },
    },
    chunkSizeWarningLimit: 900,
  },
  server: {
    port: 3000,
    host: true,
  },
});
