export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

const UNREACHABLE =
  'The API server is not responding. Make sure it is running on port 8000.'

/** GET a JSON resource from the FastAPI backend (proxied at /api). */
export async function apiGet<T>(path: string, signal?: AbortSignal): Promise<T> {
  let response: Response
  try {
    response = await fetch(`/api${path}`, { signal, headers: { Accept: 'application/json' } })
  } catch (error) {
    if (signal?.aborted) throw error
    throw new ApiError(0, UNREACHABLE)
  }

  if (!response.ok) {
    throw new ApiError(response.status, await errorMessage(response))
  }
  return (await response.json()) as T
}

/** POST JSON. Used only for actions that start live investigations. */
export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  let response: Response
  try {
    response = await fetch(`/api${path}`, {
      method: 'POST',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new ApiError(0, UNREACHABLE)
  }
  if (!response.ok) throw new ApiError(response.status, await errorMessage(response))
  return (await response.json()) as T
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json()
    if (body && typeof body === 'object' && 'detail' in body) {
      if (typeof body.detail === 'string') return body.detail
      if (Array.isArray(body.detail)) return 'Please check the question: it must be 5 to 600 characters.'
    }
  } catch {
    // Not JSON: usually the dev proxy reporting that the backend is down.
  }
  return response.status >= 500 ? UNREACHABLE : `Request failed (${response.status})`
}
