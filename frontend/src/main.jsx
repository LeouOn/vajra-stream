/**
 * Vajra.Stream Frontend Entry Point.
 *
 * Mounts the root ``<App />`` component into the DOM with React StrictMode.
 * Imports Tailwind CSS (index.css) and global component styles (globals.css).
 */
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'
import './styles/globals.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)