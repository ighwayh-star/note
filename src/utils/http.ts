export class HttpError extends Error {
  status: number
  body: unknown

  constructor(status: number, message: string, body: unknown) {
    super(message)
    this.status = status
    this.body = body
  }
}

type Json = Record<string, unknown> | unknown[]

export async function httpJson<T>(
  input: RequestInfo | URL,
  init: RequestInit & { json?: Json } = {},
): Promise<T> {
  const headers = new Headers(init.headers)
  if (!headers.has('Content-Type') && init.json) headers.set('Content-Type', 'application/json')
  const res = await fetch(input, {
    ...init,
    headers,
    body: init.json ? JSON.stringify(init.json) : init.body,
  })
  const contentType = res.headers.get('content-type') || ''
  const body = contentType.includes('application/json') ? await res.json() : await res.text()

  if (!res.ok) {
    const message = typeof body === 'string' ? body : (body as any)?.detail || res.statusText
    throw new HttpError(res.status, String(message), body)
  }
  return body as T
}

