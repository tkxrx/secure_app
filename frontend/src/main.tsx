import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './style.css'

// BrowserRouter даёт маршрутизацию по обычным путям; на сервере их обслуживает try_files в nginx.conf.
createRoot(document.getElementById('root')!).render(
  <BrowserRouter>
    <App />
  </BrowserRouter>,
)
