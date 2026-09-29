import React from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AIProvider } from './context/AIContext'
import App from './App'
import './index.css'

const qc = new QueryClient()
createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <AIProvider>
          <App />
        </AIProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>
)
