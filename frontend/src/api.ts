// Обёртка над fetch: добавляет JWT и превращает ответ с ошибкой в Error с текстом detail от backend.
export async function request(method: string, url: string, body?: unknown) {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const token = localStorage.getItem('token')
  if (token) headers['Authorization'] = 'Bearer ' + token

  const res = await fetch(url, {
    method,
    headers,
    // У GET и DELETE тела нет.
    body: body ? JSON.stringify(body) : undefined,
  })
  // У ответа может не быть JSON-тела, тогда работаем с пустым объектом.
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    throw new Error(data.detail || 'Ошибка ' + res.status)
  }
  return data
}
