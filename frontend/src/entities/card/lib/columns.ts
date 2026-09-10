import type { CardColumn, CardType } from '@/shared/api'

/** Колонки доски в том порядке, в котором их рисуем */
export const COLUMNS: { id: CardColumn; title: string }[] = [
  { id: 'event', title: 'События' },
  { id: 'idea', title: 'Идеи' },
  { id: 'question', title: 'Вопросы' },
  { id: 'accepted', title: 'Принято' },
  { id: 'rejected', title: 'Отклонено' },
]

/** Типы, которые можно выбрать для карточки */
export const CARD_TYPES: CardType[] = ['event', 'idea', 'question']

// Record<CardType, string> требует подпись для каждого типа: забудем один — TypeScript подскажет
export const TYPE_LABELS: Record<CardType, string> = {
  event: 'Событие',
  idea: 'Идея',
  question: 'Вопрос',
}
