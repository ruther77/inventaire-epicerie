import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

const appHistoryFallback = {
  disableDotRule: true,
  rewrites: [{ from: /^\/app(?:\/.*)?$/, to: '/app/index.html' }],
};

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
    historyApiFallback: appHistoryFallback,
  },
  preview: {
    port: 5173,
    historyApiFallback: appHistoryFallback,
  },
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        app: resolve(__dirname, 'app/index.html'),
      },
    },
  },
});
