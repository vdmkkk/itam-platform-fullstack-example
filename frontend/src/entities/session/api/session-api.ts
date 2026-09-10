import { request, type Profile, type ProfileUpdate } from '@/shared/api'

/** Кто я. С `token` — проверить конкретный токен (перед входом) */
export function getMe(token?: string) {
  return request<Profile>('/api/me', { token })
}

export function updateMe(changes: ProfileUpdate) {
  return request<Profile>('/api/me', { method: 'PATCH', body: changes })
}
