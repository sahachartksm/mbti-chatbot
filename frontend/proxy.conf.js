// Angular dev-server proxy config (Vite-compatible object format)
// Forwards /api/* requests to the Go backend so frontend can use relative URLs
// Native dev:   API_TARGET not set → falls back to http://localhost:8080
// Docker dev:   docker-compose sets API_TARGET=http://backend:8080

const target = process.env.API_TARGET || 'http://localhost:8080';

module.exports = {
  '/api': {
    target,
    secure: false,
    changeOrigin: true,
    logLevel: 'debug',
  },
};
