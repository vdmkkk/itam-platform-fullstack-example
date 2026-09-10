import { memo } from 'react'
import type { Card } from '@/shared/api'
import { cn, formatDateTime } from '@/shared/lib'
import { TypeBadge } from './TypeBadge'
import styles from './CardPreview.module.css'

type Props = {
  card: Card
  onOpen: (cardId: string) => void
}

// memo: пока `card` и `onOpen` те же самые, React не перерисовывает карточку.
// Например, при вводе в поиск перерисуются колонки, но не каждая карточка в них.
export const CardPreview = memo(function CardPreview({ card, onOpen }: Props) {
  return (
    <button type="button" className={styles.card} onClick={() => onOpen(card.id)}>
      {card.preview && <img className={styles.image} src={card.preview} alt="" loading="lazy" />}

      <span className={styles.top}>
        <TypeBadge type={card.type} />
        {card.date !== null && <span className={styles.date}>📅 {formatDateTime(card.date)}</span>}
      </span>

      <span className={styles.title}>{card.title}</span>

      <span className={styles.meta}>
        <span className={styles.author}>
          {card.author.name}
          {card.is_mine && ' (вы)'}
        </span>
        <span className={styles.stats}>
          <span className={cn(styles.score, card.my_vote && styles[card.my_vote])} title="Счёт">
            {card.score > 0 ? `+${card.score}` : card.score}
          </span>
          <span title="Комментарии">💬 {card.comments_count}</span>
        </span>
      </span>
    </button>
  )
})
