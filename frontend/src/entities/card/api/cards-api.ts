import { request, type Card, type CardCreate, type CardUpdate, type VoteValue } from '@/shared/api'

export function getCards() {
  return request<Card[]>('/api/cards')
}

export function createCard(body: CardCreate) {
  return request<Card>('/api/cards', { method: 'POST', body })
}

export function updateCard(cardId: string, changes: CardUpdate) {
  return request<Card>(`/api/cards/${cardId}`, { method: 'PATCH', body: changes })
}

export function deleteCard(cardId: string) {
  return request<void>(`/api/cards/${cardId}`, { method: 'DELETE' })
}

export function voteCard(cardId: string, value: VoteValue) {
  return request<Card>(`/api/cards/${cardId}/vote`, { method: 'PUT', body: { value } })
}

export function removeVote(cardId: string) {
  return request<Card>(`/api/cards/${cardId}/vote`, { method: 'DELETE' })
}
