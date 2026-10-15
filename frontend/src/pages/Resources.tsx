import { useEffect, useState } from 'react'
import { request } from '../api'

type Rights = { read: boolean; update: boolean; delete: boolean }
type Resource = { id: number; title: string; owner: string; rights: Rights; content?: string }

function rightsText(r: Rights) {
  const list = []
  if (r.read) list.push('чтение')
  if (r.update) list.push('изменение')
  if (r.delete) list.push('удаление')
  return list.length ? list.join(', ') : 'нет прав'
}

export default function Resources() {
  const [resources, setResources] = useState<Resource[]>([])
  const [selected, setSelected] = useState<Resource | null>(null)
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [editText, setEditText] = useState('')
  const [grantLogin, setGrantLogin] = useState('')
  const [canRead, setCanRead] = useState(true)
  const [canUpdate, setCanUpdate] = useState(false)
  const [canDelete, setCanDelete] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const me = localStorage.getItem('login')

  async function load() {
    try {
      setResources(await request('GET', '/api/resources'))
    } catch (err: any) {
      setError(err.message)
    }
  }

  useEffect(() => {
    load()
  }, [])

  function clear() {
    setMessage('')
    setError('')
  }

  async function open(id: number) {
    clear()
    setSelected(null)
    try {
      const data = await request('GET', '/api/resources/' + id)
      setSelected(data)
      setEditText(data.content)
    } catch (err: any) {
      setError('Ресурс #' + id + ': ' + err.message)
    }
  }

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
      const data = await request('PUT', '/api/resources/' + selected.id, { content: editText })
      setMessage(data.message)
      open(selected.id)
    } catch (err: any) {
      setError(err.message)
    }
  }

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
