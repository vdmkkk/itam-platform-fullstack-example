import type { FieldError } from './types'

const API_URL = import.meta.env.VITE_API_URL ?? 'https://courses.salut.uno/example-backend/frontend-itam'

// Токен курса: страница курса → вкладка «API проекта». Вставьте сюда свой.
// В коде его видно всем, но он открывает только учебный API, поэтому здесь так можно
const COURSE_TOKEN = 'exb_wQJrgcI2bQf0jrfy69ViFPqQman3pver'

/** Ошибка от API. `fieldErrors` — ошибки конкретных полей формы (приходят с 422 и 409). */
export class ApiError extends Error {
  readonly status: number
  readonly fieldErrors: FieldError[]

  constructor(status: number, message: string, fieldErrors: FieldError[] = []) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.fieldErrors = fieldErrors
  }
}

type RequestOptions = {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: unknown
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body } = options
  // Токен уходит в каждом запросе: по нему API узнаёт, кто вы
  const headers: Record<string, string> = { 'X-Course-Token': COURSE_TOKEN }
  if (body !== undefined) headers['Content-Type'] = 'application/json'

  let response: Response
  try {
    response = await fetch(API_URL + path, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new ApiError(0, 'Сервер не отвечает. Проверьте интернет и попробуйте ещё раз.')
  }

  // 204 No Content: тела нет, и response.json() упал бы с ошибкой
  if (response.status === 204) return undefined as T

  const data = await response.json().catch(() => null)
  if (!response.ok) {
    // Бэкенд всегда отвечает на ошибки так: { detail: "...", errors?: [{ field, message }] }
    throw new ApiError(response.status, data?.detail ?? `Ошибка ${response.status}`, data?.errors ?? [])
  }
  return data as T
}

export function getErrorMessage(error: unknown) {
  return error instanceof Error ? error.message : 'Что-то пошло не так'
}
