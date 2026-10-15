import { useState } from 'react'
import { request } from '../api'

export default function Register() {
  const [login, setLogin] = useState('')
  const [password, setPassword] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setMessage('')
    setError('')
    try {
      const data = await request('POST', '/api/register', { login, password })
      setMessage(data.message)
      setPassword('')
    } catch (err: any) {
      setError(err.message)
    }
  }

  return (
    <div className="card">
      <h2>Регистрация</h2>
      <form onSubmit={onSubmit}>
        <input name="login" placeholder="Логин" value={login} onChange={(e) => setLogin(e.target.value)} />
        <input
          name="password"
          type="password"
          placeholder="Пароль"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <small>
          Пароль: от 8 символов, заглавная и строчная буква, цифра, спецсимвол
        </small>
        <button type="submit">Зарегистрироваться</button>
      </form>
      {message && <p className="success">{message}</p>}
      {error && <p className="error">{error}</p>}
    </div>
  )
}
