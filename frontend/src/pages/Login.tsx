import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { request } from '../api'

export default function Login() {
  const [login, setLogin] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate()

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    try {
      const data = await request('POST', '/api/login', { login, password })
      // Токен кладётся в localStorage, его подставляет request() в каждый запрос.
      localStorage.setItem('token', data.access_token)
      localStorage.setItem('login', login)
      // После входа пользователь попадает на страницу ресурсов.
      navigate('/resources')
    } catch (err: any) {
      setError(err.message)
    }
  }

  return (
    <div className="card">
      <h2>Вход</h2>
      <form onSubmit={onSubmit}>
        <input name="login" placeholder="Логин" value={login} onChange={(e) => setLogin(e.target.value)} />
        <input
          name="password"
          type="password"
          placeholder="Пароль"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <button type="submit">Войти</button>
      </form>
      {error && <p className="error">{error}</p>}
    </div>
  )
}
