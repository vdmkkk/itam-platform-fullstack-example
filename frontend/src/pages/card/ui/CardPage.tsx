import { useEffect, type ReactNode } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { useCardsStore } from '@/entities/card'
import { CardForm } from '@/features/card-form'
import { routes } from '@/shared/config'
import { ErrorMessage, Loader } from '@/shared/ui'
import styles from './CardPage.module.css'

/** Страница карточки нужна только для редактирования. Смотрят и обсуждают карточку в модалке */
export function CardPage() {
  const { cardId = '' } = useParams()
  const navigate = useNavigate()
  const card = useCardsStore((state) => state.cards.find((item) => item.id === cardId))
  const status = useCardsStore((state) => state.status)
  const error = useCardsStore((state) => state.error)
  const loadCards = useCardsStore((state) => state.loadCards)

  // Страницу открыли по ссылке, минуя доску: карточек в сторе ещё нет — загрузим
  useEffect(() => {
    if (status === 'idle') loadCards()
  }, [status, loadCards])

  function backToBoard() {
    navigate(routes.board())
  }

  let content: ReactNode
  if (card?.is_mine) {
    content = <CardForm card={card} onDone={backToBoard} onCancel={backToBoard} />
  } else if (card) {
    content = <p className={styles.muted}>Редактировать можно только свои карточки.</p>
  } else if (status === 'error') {
    content = <ErrorMessage message={error ?? 'Не удалось загрузить карточку'} onRetry={loadCards} />
  } else if (status === 'ready') {
    content = <p className={styles.muted}>Карточка не найдена. Возможно, её удалили.</p>
  } else {
    content = <Loader />
  }

  return (
    <div className={styles.page}>
      <Link to={routes.board()} className={styles.back}>
        ← К доске
      </Link>
      <section className={styles.card}>
        <h1 className={styles.title}>Редактирование карточки</h1>
        {content}
      </section>
    </div>
  )
}
