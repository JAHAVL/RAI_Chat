const path = require('path');
const HtmlWebpackPlugin = require('html-webpack-plugin');

module.exports = {
  cache: false, // Disable webpack cache
  entry: './src/index.tsx', // Restore original entry point
  output: {
    path: path.resolve(__dirname, 'build'),
    filename: 'bundle.js',
    publicPath: '/' // Use root-relative path for SPA routing
  },
  resolve: {
    extensions: ['.js', '.jsx', '.ts', '.tsx'],
    fallback: {
      "buffer": require.resolve("buffer/"),
      "process": require.resolve("process/browser"),
      "path": require.resolve("path-browserify") // Add fallback for path module
    }
  },
  module: {
    rules: [
      {
        test: /\.(js|jsx|ts|tsx)$/,
        exclude: /node_modules/,
        use: {
          loader: 'babel-loader',
          options: {
            presets: [
              '@babel/preset-env',
              ['@babel/preset-react', { runtime: 'automatic' }],
              '@babel/preset-typescript'
            ]
          }
        }
      },
      {
        test: /\.css$/,
        use: ['style-loader', 'css-loader']
      },
      {
        test: /\.(png|svg|jpg|jpeg|gif)$/i,
        type: 'asset/resource',
      }
    ]
  },
  plugins: [
    new HtmlWebpackPlugin({
      template: './public/index.html',
      filename: 'index.html'
    }),
    // Add ProvidePlugin to automatically load modules
    new (require('webpack').ProvidePlugin)({
      process: 'process/browser',
      Buffer: ['buffer', 'Buffer'],
    }),
  ],
  devServer: {
    static: path.join(__dirname, 'public'), // Serve static files from public directory
    compress: true,
    port: 8081, // Match the port specified in package.json
    hot: true,
    historyApiFallback: true, // Needed for client-side routing
    host: '0.0.0.0', // Allow access from any IP address
    proxy: [{
        context: ['/api'],
        target: 'http://backend:6102',
        secure: false,
        changeOrigin: true,
        logLevel: 'debug',
        timeout: 120000,  // 2 minute timeout
        proxyTimeout: 120000,
        onProxyReq: (proxyReq) => {
          console.log('Proxying request to backend:', proxyReq.path);
        },
        onProxyRes: (proxyRes) => {
          console.log('Received response from backend:', proxyRes.statusCode);
        },
        onError: (err, req, res) => {
          console.error('Proxy error:', err);
          res.writeHead(500, {
            'Content-Type': 'application/json'
          });
          res.end(JSON.stringify({
            status: 'error',
            error: `Proxy error: ${err.message || 'Unknown error'}`,
            code: err.code || 'UNKNOWN'
          }));
        }
      },
      {
        context: ['/llm-api'],
        target: 'http://llm-engine:6101',
        pathRewrite: { '^/llm-api': '/api' },
        secure: false,
        changeOrigin: true,
        logLevel: 'debug',
        timeout: 120000, // 2 minute timeout
        proxyTimeout: 120000,
        onProxyReq: (proxyReq) => {
          console.log('Proxying request to LLM engine:', proxyReq.path);
        },
        onProxyRes: (proxyRes) => {
          console.log('Received response from LLM engine:', proxyRes.statusCode);
        },
        onError: (err, req, res) => {
          console.error('LLM Proxy error:', err);
          res.writeHead(500, {
            'Content-Type': 'application/json'
          });
          res.end(JSON.stringify({
            status: 'error',
            error: `LLM Proxy error: ${err.message || 'Unknown error'}`,
            code: err.code || 'UNKNOWN'
          }));
        }
      }]
  },
  target: 'web' // Target web environment
};
