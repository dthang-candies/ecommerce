const TOKEN_KEY = 'unicart.token'

export class ApiError extends Error {
  status: number
  code: string
  constructor(status: number, code: string, message: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

export const tokenStore = {
  get(): string | null {
    try { return localStorage.getItem(TOKEN_KEY) } catch { return null }
  },
  set(token: string | null) {
    try { token ? localStorage.setItem(TOKEN_KEY, token) : localStorage.removeItem(TOKEN_KEY) } catch { /* private mode */ }
  },
}

let onUnauthorized: () => void = () => {}
export const setUnauthorizedHandler = (fn: () => void) => { onUnauthorized = fn }

type Query = Record<string, string | number | boolean | null | undefined>

export function qs(params: Query): string {
  const p = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== null && v !== '') p.set(k, String(v)) })
  const s = p.toString()
  return s ? `?${s}` : ''
}

async function request<T>(method: string, path: string, body?: unknown, timeoutMs = 0): Promise<T> {
  const headers: Record<string, string> = {}
  const token = tokenStore.get()
  if (token) headers.Authorization = `Bearer ${token}`
  const raw = body instanceof Blob
  if (body !== undefined) headers['Content-Type'] = raw ? body.type || 'application/octet-stream' : 'application/json'
  const ctl = new AbortController()
  const timer = timeoutMs ? setTimeout(() => ctl.abort(), timeoutMs) : undefined
  let res: Response
  try {
    res = await fetch(`/api${path}`, { method, headers, signal: ctl.signal, body: body === undefined ? undefined : raw ? body : JSON.stringify(body) })
  } catch (e) {
    if (e instanceof DOMException && e.name === 'AbortError') throw new ApiError(0, 'TIMEOUT', 'Máy chủ phản hồi quá lâu, vui lòng thử lại.')
    throw new ApiError(0, 'NETWORK', 'Không kết nối được máy chủ. Vui lòng kiểm tra mạng và thử lại.')
  } finally {
    if (timer) clearTimeout(timer)
  }
  if (res.status === 204) return undefined as T
  const data = await res.json().catch(() => null)
  if (!res.ok) {
    if (res.status === 401 && token) onUnauthorized()
    throw new ApiError(res.status, data?.error ?? 'ERROR', data?.message ?? `Lỗi ${res.status}`)
  }
  return data as T
}

export const api = {
  get: <T>(path: string, params?: Query) => request<T>('GET', path + (params ? qs(params) : '')),
  post: <T>(path: string, body?: unknown) => request<T>('POST', path, body ?? {}),
  put: <T>(path: string, body: unknown) => request<T>('PUT', path, body),
  patch: <T>(path: string, body: unknown) => request<T>('PATCH', path, body),
  del: <T>(path: string) => request<T>('DELETE', path),
  /** Sends a file (image / audio) as the raw request body, e.g. for AI search. */
  upload: <T>(path: string, file: Blob, params?: Query) => request<T>('POST', path + (params ? qs(params) : ''), file, 45000),
}

export const errorMessage = (e: unknown): string => (e instanceof Error ? e.message : 'Đã xảy ra lỗi, vui lòng thử lại')
