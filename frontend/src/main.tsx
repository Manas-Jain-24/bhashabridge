import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import {AccountShell} from './components/AccountShell'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <AccountShell><App /></AccountShell>
  </React.StrictMode>,
)
