import { Link, Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import Register from './pages/Register'
import Login from './pages/Login'
import Resources from './pages/Resources'

export default function App() {
  const navigate = useNavigate()
  // login хранится только для отображения; доступ определяет токен, который проверяет сервер.
  const login = localStorage.getItem('login')

  function logout() {
    localStorage.removeItem('token')
    localStorage.removeItem('login')
    navigate('/login')
  }

  return (
    <div className="container">
      <nav>
        <Link to="/register">Регистрация</Link>
        <Link to="/login">Вход</Link>
        <Link to="/resources">Ресурсы</Link>
        {login && (
          <span className="user">
            {login} <button onClick={logout}>выйти</button>
          </span>
        )}
      </nav>
      <Routes>
        <Route path="/register" element={<Register />} />
        <Route path="/login" element={<Login />} />
        <Route path="/resources" element={<Resources />} />
        {/* Любой неизвестный путь ведёт на регистрацию. */}
        <Route path="*" element={<Navigate to="/register" />} />
      </Routes>
    </div>
  )
}
