import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { filterCards, useCardsStore } from '@/entities/card'
import { CardForm } from '@/features/card-form'
import { CardFilters } from '@/features/filter-cards'
import { Button, ErrorMessage, Loader, Modal } from '@/shared/ui'
import { BoardColumns } from '@/widgets/board-columns'
import { CardModal } from '@/widgets/card-modal'
import styles from './BoardPage.module.css'

export function BoardPage() {
  const cards = useCardsStore((state) => state.cards)
  const status = useCardsStore((state) => state.status)
  const error = useCardsStore((state) => state.error)
  const filters = useCardsStore((state) => state.filters)
  const loadCards = useCardsStore((state) => state.loadCards)

  const [openCardId, setOpenCardId] = useState<string | null>(null)
  const [isCreating, setIsCreating] = useState(false)

  // Каждый раз, когда открываем доску, подтягиваем свежие карточки
  useEffect(() => {
    loadCards()
  }, [loadCards])

  // Пересчитываем, только когда поменялись карточки или фильтры, а не на каждый рендер
  const visibleCards = useMemo(() => filterCards(cards, filters), [cards, filters])

  let content: ReactNode
  if (status === 'error') {
    content = <ErrorMessage message={error ?? 'Не удалось загрузить карточки'} onRetry={loadCards} />
  } else if (status !== 'ready' && cards.length === 0) {
    content = <Loader />
  } else {
    // setOpenCardId — одна и та же функция между рендерами, поэтому memo в CardPreview работает
    content = <BoardColumns cards={visibleCards} onOpenCard={setOpenCardId} />
  }

  return (
    <div className={styles.page}>
      <div className={styles.toolbar}>
        <CardFilters />
        <Button variant="primary" onClick={() => setIsCreating(true)}>
          + Новая карточка
        </Button>
      </div>

      {status === 'ready' && cards.length === 0 && (
        <p className={styles.hint}>Карточек пока нет — создайте первую!</p>
      )}
      {content}

      {openCardId && <CardModal cardId={openCardId} onClose={() => setOpenCardId(null)} />}

      {isCreating && (
        <Modal title="Новая карточка" onClose={() => setIsCreating(false)}>
          <CardForm onDone={() => setIsCreating(false)} onCancel={() => setIsCreating(false)} />
        </Modal>
      )}
    </div>
  )
}
