import { Link, Navigate, Route, Routes } from 'react-router-dom'
import Register from './pages/Register'

export default function App() {
  return (
    <div className="container">
      <nav>
        <Link to="/register">Регистрация</Link>
      </nav>
      <Routes>
        <Route path="/register" element={<Register />} />
        <Route path="*" element={<Navigate to="/register" />} />
      </Routes>
    </div>
  )
}
