import { request, type Comment } from '@/shared/api'

export function addComment(cardId: string, text: string) {
  return request<Comment>(`/api/cards/${cardId}/comments`, { method: 'POST', body: { text } })
}

export function deleteComment(commentId: string) {
  return request<void>(`/api/comments/${commentId}`, { method: 'DELETE' })
}
