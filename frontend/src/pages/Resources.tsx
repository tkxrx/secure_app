import { useEffect, useState } from 'react'
import { request } from '../api'

// Права приходят с сервера, клиент их только показывает.
type Rights = { read: boolean; update: boolean; delete: boolean }
// content есть только в ответе GET /api/resources/{id}, в списке его нет.
type Resource = { id: number; title: string; owner: string; rights: Rights; content?: string }

// Права в виде строки для колонки «Мои права».
function rightsText(r: Rights) {
  const list = []
  if (r.read) list.push('чтение')
  if (r.update) list.push('изменение')
  if (r.delete) list.push('удаление')
  return list.length ? list.join(', ') : 'нет прав'
}

export default function Resources() {
  const [resources, setResources] = useState<Resource[]>([])
  // Открытый ресурс с содержимым; null - ничего не открыто.
  const [selected, setSelected] = useState<Resource | null>(null)
  // Поля формы создания ресурса.
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  // Редактируемое содержимое открытого ресурса.
  const [editText, setEditText] = useState('')
  // Форма выдачи прав: кому и какие права.
  const [grantLogin, setGrantLogin] = useState('')
  const [canRead, setCanRead] = useState(true)
  const [canUpdate, setCanUpdate] = useState(false)
  const [canDelete, setCanDelete] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  // Логин текущего пользователя: форма выдачи прав показывается только владельцу ресурса.
  const me = localStorage.getItem('login')

  async function load() {
    try {
      setResources(await request('GET', '/api/resources'))
    } catch (err: any) {
      setError(err.message)
    }
  }

  // Список загружается один раз при открытии страницы.
  useEffect(() => {
    load()
  }, [])

  function clear() {
    setMessage('')
    setError('')
  }

  async function open(id: number) {
    clear()
    // Сбрасываем выбранный ресурс, чтобы при ошибке (403) не остался открытым предыдущий.
    setSelected(null)
    try {
      const data = await request('GET', '/api/resources/' + id)
      setSelected(data)
      setEditText(data.content)
    } catch (err: any) {
      setError('Ресурс #' + id + ': ' + err.message)
    }
  }

  // Создаёт ресурс и перечитывает список.
  async function create(e: React.FormEvent) {
    e.preventDefault()
    clear()
    try {
      await request('POST', '/api/resources', { title, content })
      setTitle('')
      setContent('')
      load()
    } catch (err: any) {
      setError(err.message)
    }
  }

  async function save() {
    if (!selected) return
    clear()
    try {
      // Отправляется только content, название не меняется.
      const data = await request('PUT', '/api/resources/' + selected.id, { content: editText })
      setMessage(data.message)
      // Перечитываем ресурс, чтобы показать сохранённое состояние.
      open(selected.id)
    } catch (err: any) {
      setError(err.message)
    }
  }

  // Удаляет открытый ресурс и перечитывает список.
  async function remove() {
    if (!selected) return
    clear()
    try {
      const data = await request('DELETE', '/api/resources/' + selected.id)
      setMessage(data.message)
      setSelected(null)
      load()
    } catch (err: any) {
      setError(err.message)
    }
  }

  async function grant(e: React.FormEvent) {
    e.preventDefault()
    if (!selected) return
    clear()
    try {
      // Повторная выдача тому же пользователю заменяет его права целиком.
      const data = await request('POST', '/api/resources/' + selected.id + '/permissions', {
        login: grantLogin,
        can_read: canRead,
        can_update: canUpdate,
        can_delete: canDelete,
      })
      setMessage(data.message)
      setGrantLogin('')
    } catch (err: any) {
      setError(err.message)
    }
  }

  // Проверка стоит после всех хуков, иначе нарушится порядок хуков между рендерами.
  if (!localStorage.getItem('token')) {
    return <p>Сначала войдите в систему.</p>
  }

  return (
    <div>
      <h2>Ресурсы</h2>
      <table>
        <thead>
          <tr>
            <th>id</th>
            <th>Название</th>
            <th>Владелец</th>
            <th>Мои права</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {resources.map((r) => (
            <tr key={r.id}>
              <td>{r.id}</td>
              <td>{r.title}</td>
              <td>{r.owner}</td>
              <td>{rightsText(r.rights)}</td>
              <td>
                <button onClick={() => open(r.id)}>Открыть</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {message && <p className="success">{message}</p>}
      {error && <p className="error">{error}</p>}

      {selected && (
        <div className="card">
          <h3>
            {selected.title} (владелец: {selected.owner})
          </h3>
          <textarea rows={4} value={editText} onChange={(e) => setEditText(e.target.value)} />
          <div>
            <button onClick={save}>Сохранить</button> <button onClick={remove}>Удалить</button>
          </div>

          {selected.owner === me && (
            <form onSubmit={grant} className="grant">
              <h4>Выдать права</h4>
              <input placeholder="Логин пользователя" value={grantLogin} onChange={(e) => setGrantLogin(e.target.value)} />
              <label>
                <input type="checkbox" checked={canRead} onChange={(e) => setCanRead(e.target.checked)} /> чтение
              </label>
              <label>
                <input type="checkbox" checked={canUpdate} onChange={(e) => setCanUpdate(e.target.checked)} /> изменение
              </label>
              <label>
                <input type="checkbox" checked={canDelete} onChange={(e) => setCanDelete(e.target.checked)} /> удаление
              </label>
              <button type="submit">Выдать</button>
            </form>
          )}
        </div>
      )}

      <div className="card">
        <h3>Новый ресурс</h3>
        <form onSubmit={create}>
          <input placeholder="Название" value={title} onChange={(e) => setTitle(e.target.value)} />
          <textarea placeholder="Содержимое" rows={3} value={content} onChange={(e) => setContent(e.target.value)} />
          <button type="submit">Создать</button>
        </form>
      </div>
    </div>
  )
}
