import { request, type Profile, type ProfileUpdate } from '@/shared/api'

/** Кто я: владелец токена из `shared/api/client.ts` */
export function getMe() {
  return request<Profile>('/api/me')
}

export function updateMe(changes: ProfileUpdate) {
  return request<Profile>('/api/me', { method: 'PATCH', body: changes })
}
