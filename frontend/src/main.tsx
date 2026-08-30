/**
 * Vajra.Stream Frontend Entry Point.
 *
 * Mounts the root ``<App />`` component into the DOM with React StrictMode.
 * Imports Tailwind CSS (index.css) and global component styles (globals.css).
 */
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'
import './styles/globals.css'

// Suppress verbose console.log in production builds; warn/error stay visible.
// The `logger.ts` utility is unaffected — it routes through these same methods.
if (import.meta.env.PROD) {
  console.log = () => {};
}

const rootElement: HTMLElement | null = document.getElementById('root');

if (!rootElement) {
  throw new Error('Root element #root not found in document');
}

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)