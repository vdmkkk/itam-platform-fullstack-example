import type { Card, CardColumn, CardSort } from '@/shared/api'

export type CardFilters = {
  search: string
  onlyMine: boolean
  sort: CardSort
}

export const DEFAULT_FILTERS: CardFilters = { search: '', onlyMine: false, sort: 'new' }

const newestFirst = (a: Card, b: Card) => b.created_at - a.created_at

const COMPARE: Record<CardSort, (a: Card, b: Card) => number> = {
  new: newestFirst,
  old: (a, b) => a.created_at - b.created_at,
  top: (a, b) => b.score - a.score || newestFirst(a, b),
}

/**
 * Карточки, которые проходят фильтры, в нужном порядке.
 * Чистая функция: исходный массив не меняет, для одинаковых аргументов даёт одинаковый результат.
 */
export function filterCards(cards: Card[], { search, onlyMine, sort }: CardFilters) {
  const query = search.trim().toLowerCase()
  return cards
    .filter((card) => !onlyMine || card.is_mine)
    .filter((card) => `${card.title} ${card.description ?? ''}`.toLowerCase().includes(query))
    .toSorted(COMPARE[sort])
}

/** Раскладывает карточки по колонкам: { event: [...], idea: [...], ... } */
export function groupByColumn(cards: Card[]) {
  const groups: Record<CardColumn, Card[]> = { event: [], idea: [], question: [], accepted: [], rejected: [] }
  for (const card of cards) {
    groups[card.column].push(card)
  }
  return groups
}
