import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { extname, resolve } from 'node:path';

const APP_ENTRY_PATH = '/app/index.html';
const APP_BASE_PATH = '/app';

const acceptsHtml = (request) =>
  typeof request.headers.accept === 'string' && request.headers.accept.includes('text/html');

const createAppHistoryFallbackMiddleware = () => (req, _res, next) => {
  if (!req?.url || !req.method || !['GET', 'HEAD'].includes(req.method.toUpperCase())) {
    next();
    return;
  }

  const url = req.url.split('?')[0];
  if (!url.startsWith(APP_BASE_PATH) || url === APP_ENTRY_PATH || extname(url)) {
    next();
    return;
  }

  if (!acceptsHtml(req)) {
    next();
    return;
  }

  req.url = APP_ENTRY_PATH;
  next();
};

const appHistoryFallbackPlugin = () => ({
  name: 'app-history-fallback',
  configureServer(server) {
    server.middlewares.use(createAppHistoryFallbackMiddleware());
  },
  configurePreviewServer(server) {
    server.middlewares.use(createAppHistoryFallbackMiddleware());
  },
});

export default defineConfig({
  plugins: [react(), appHistoryFallbackPlugin()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
  preview: {
    port: 5173,
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
