import { request, type UserDetail } from '@/shared/api'

export function getUser(userId: string) {
  return request<UserDetail>(`/api/users/${userId}`)
}
