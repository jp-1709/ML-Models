const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function (app) {
    // Proxy HTTP requests
    app.use(
        '/api',
        createProxyMiddleware({
            target: 'http://localhost:8000',
            changeOrigin: true,
        })
    );
    app.use(
        '/video_feed',
        createProxyMiddleware({
            target: 'http://localhost:8000',
            changeOrigin: true,
        })
    );
    // Proxy WebSocket requests with custom path to avoid Webpack /ws collision
    app.use(
        '/backend-ws',
        createProxyMiddleware({
            target: 'http://localhost:8000',
            ws: true,
            changeOrigin: true,
            pathRewrite: { '^/backend-ws': '/ws' },
        })
    );
};
