import { create } from 'zustand'
import { getErrorMessage, type Card, type CardCreate, type CardUpdate, type VoteValue } from '@/shared/api'
import * as cardsApi from '../api/cards-api'
import { DEFAULT_FILTERS, type CardFilters } from './filter-cards'

type CardsState = {
  cards: Card[]
  status: 'idle' | 'loading' | 'ready' | 'error'
  error: string | null
  filters: CardFilters

  loadCards: () => Promise<void>
  createCard: (body: CardCreate) => Promise<Card>
  updateCard: (cardId: string, changes: CardUpdate) => Promise<Card>
  deleteCard: (cardId: string) => Promise<void>
  vote: (cardId: string, value: VoteValue | null) => Promise<Card>
  changeCommentsCount: (cardId: string, delta: number) => void
  setFilters: (changes: Partial<CardFilters>) => void
}

/** Новый массив, где заменена одна карточка. Остальные — те же самые объекты, и memo это ценит */
function replaceCard(cards: Card[], updated: Card) {
  return cards.map((card) => (card.id === updated.id ? updated : card))
}

// Общий стор карточек: доска, модалка, страница карточки и страница пользователя берут данные отсюда
export const useCardsStore = create<CardsState>()((set) => ({
  cards: [],
  status: 'idle',
  error: null,
  filters: DEFAULT_FILTERS,

  loadCards: async () => {
    set({ status: 'loading', error: null })
    try {
      const cards = await cardsApi.getCards()
      set({ cards, status: 'ready' })
    } catch (err) {
      set({ status: 'error', error: getErrorMessage(err) })
    }
  },

  createCard: async (body) => {
    const card = await cardsApi.createCard(body)
    set((state) => ({ cards: [card, ...state.cards] }))
    return card
  },

  updateCard: async (cardId, changes) => {
    const card = await cardsApi.updateCard(cardId, changes)
    set((state) => ({ cards: replaceCard(state.cards, card) }))
    return card
  },

  deleteCard: async (cardId) => {
    await cardsApi.deleteCard(cardId)
    set((state) => ({ cards: state.cards.filter((card) => card.id !== cardId) }))
  },

  vote: async (cardId, value) => {
    // value === null — отозвать свой голос
    const card = value ? await cardsApi.voteCard(cardId, value) : await cardsApi.removeVote(cardId)
    set((state) => ({ cards: replaceCard(state.cards, card) }))
    return card
  },

  // Сами комментарии живут в модалке, а счётчик 💬 на превью берётся отсюда — держим его в курсе
  changeCommentsCount: (cardId, delta) =>
    set((state) => ({
      cards: state.cards.map((card) =>
        card.id === cardId ? { ...card, comments_count: card.comments_count + delta } : card,
      ),
    })),

  setFilters: (changes) => set((state) => ({ filters: { ...state.filters, ...changes } })),
}))
