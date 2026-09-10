import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { CardDetails, getCard } from '@/entities/card'
import { CardForm } from '@/features/card-form'
import { DeleteCardButton } from '@/features/delete-card'
import { VoteButtons } from '@/features/vote'
import { getErrorMessage, type Card, type CardDetail, type Comment } from '@/shared/api'
import { routes } from '@/shared/config'
import { Button, ErrorMessage, Loader } from '@/shared/ui'
import { CardComments } from '@/widgets/card-comments'
import styles from './CardPage.module.css'

export function CardPage() {
  const { cardId = '' } = useParams()
  const navigate = useNavigate()
  const [card, setCard] = useState<CardDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isEditing, setIsEditing] = useState(false)

  useEffect(() => {
    // Если пользователь успел уйти на другую карточку, ответ на старый запрос выбрасываем
    let ignore = false
    getCard(cardId)
      .then((data) => {
        if (!ignore) setCard(data)
      })
      .catch((err) => {
        if (!ignore) setError(getErrorMessage(err))
      })
    return () => {
      ignore = true
    }
  }, [cardId])

  // Обновляем иммутабельно: новый объект, в котором поменялись только нужные поля
  function handleCardChanged(changed: Card) {
    setCard((prev) => prev && { ...prev, ...changed })
  }

  function handleCommentsChanged(comments: Comment[]) {
    setCard((prev) => prev && { ...prev, comments, comments_count: comments.length })
  }

  if (!card) {
    return (
      <div className={styles.page}>
        <Link to={routes.board()} className={styles.back}>
          ← К доске
        </Link>
        {error ? <ErrorMessage message={error} /> : <Loader />}
      </div>
    )
  }

  return (
    <div className={styles.page}>
      <Link to={routes.board()} className={styles.back}>
        ← К доске
      </Link>

      <article className={styles.card}>
        {isEditing ? (
          <CardForm
            card={card}
            onDone={(saved) => {
              handleCardChanged(saved)
              setIsEditing(false)
            }}
            onCancel={() => setIsEditing(false)}
          />
        ) : (
          <>
            <h1 className={styles.title}>{card.title}</h1>
            <CardDetails card={card} />
            <footer className={styles.footer}>
              <VoteButtons card={card} onVoted={handleCardChanged} />
              {card.is_mine && (
                <div className={styles.owner}>
                  <Button onClick={() => setIsEditing(true)}>Редактировать</Button>
                  <DeleteCardButton cardId={card.id} onDeleted={() => navigate(routes.board())} />
                </div>
              )}
            </footer>
          </>
        )}
      </article>

      <CardComments cardId={card.id} comments={card.comments} onChange={handleCommentsChanged} />
    </div>
  )
}
