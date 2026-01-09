import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { Provider } from 'jotai'
import './index.css'
import App from './App.tsx'

// Polyfill for Node.js globals in browser (required by @supabase/supabase-js)
if (typeof global === 'undefined') {
  window.global = window
}

createRoot(document.getElementById('root')!).render(
    <StrictMode>
        <Provider>
            <BrowserRouter>
                <App />
            </BrowserRouter>
        </Provider>
    </StrictMode>
)
