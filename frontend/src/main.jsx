import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './theme.css'
import './layout.css'
import App from './App.jsx'
import { DocumentsProvider } from './context/DocumentsContext.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <DocumentsProvider>
        <App />
      </DocumentsProvider>
    </BrowserRouter>
  </StrictMode>,
)
