import { useMemo } from 'react'
import { CardPreview, COLUMNS, groupByColumn } from '@/entities/card'
import type { Card } from '@/shared/api'
import styles from './BoardColumns.module.css'

type Props = {
  cards: Card[]
  onOpenCard: (cardId: string) => void
}

export function BoardColumns({ cards, onOpenCard }: Props) {
  // Каждая карточка попадает в колонку по своему полю column
  const groups = useMemo(() => groupByColumn(cards), [cards])

  return (
    <div className={styles.board}>
      {COLUMNS.map((column) => {
        const columnCards = groups[column.id]
        return (
          <section key={column.id} className={styles.column} data-column={column.id}>
            <h2 className={styles.title}>
              {column.title}
              <span className={styles.count}>{columnCards.length}</span>
            </h2>
            <div className={styles.list}>
              {columnCards.map((card) => (
                <CardPreview key={card.id} card={card} onOpen={onOpenCard} />
              ))}
              {columnCards.length === 0 && <p className={styles.empty}>Пока пусто</p>}
            </div>
          </section>
        )
      })}
    </div>
  )
}
