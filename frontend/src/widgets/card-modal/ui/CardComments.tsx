import { useEffect, useState, type ReactNode } from 'react'
import { useCardsStore } from '@/entities/card'
import { CommentItem, getComments } from '@/entities/comment'
import { AddCommentForm } from '@/features/add-comment'
import { DeleteCommentButton } from '@/features/delete-comment'
import { getErrorMessage, type Comment } from '@/shared/api'
import { ErrorMessage, Loader } from '@/shared/ui'
import styles from './CardComments.module.css'

/** Комментарии к карточке. Загружаются сами, как только модалка открылась */
export function CardComments({ cardId }: { cardId: string }) {
  const changeCommentsCount = useCardsStore((state) => state.changeCommentsCount)
  const [comments, setComments] = useState<Comment[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // Если модалку закрыли раньше, чем пришёл ответ, он нам уже не нужен — выбрасываем
    let ignore = false
    getComments(cardId)
      .then((data) => {
        if (!ignore) setComments(data)
      })
      .catch((err) => {
        if (!ignore) setError(getErrorMessage(err))
      })
    return () => {
      ignore = true
    }
  }, [cardId])

  // Обновляем иммутабельно: новый массив вместо изменения старого
  function handleAdded(comment: Comment) {
    setComments((prev) => prev && [...prev, comment])
    changeCommentsCount(cardId, 1)
  }

  function handleDeleted(commentId: string) {
    setComments((prev) => prev && prev.filter((comment) => comment.id !== commentId))
    changeCommentsCount(cardId, -1)
  }

  let content: ReactNode
  if (error) {
    content = <ErrorMessage message={error} />
  } else if (!comments) {
    content = <Loader />
  } else if (comments.length === 0) {
    content = <p className={styles.empty}>Пока никто не написал. Будьте первым!</p>
  } else {
    content = (
      <ul className={styles.list}>
        {comments.map((comment) => (
          <li key={comment.id}>
            <CommentItem
              comment={comment}
              actions={
                comment.is_mine && (
                  <DeleteCommentButton commentId={comment.id} onDeleted={() => handleDeleted(comment.id)} />
                )
              }
            />
          </li>
        ))}
      </ul>
    )
  }

  return (
    <section className={styles.section}>
      <h3 className={styles.title}>Комментарии{comments && ` · ${comments.length}`}</h3>
      {content}
      {comments && <AddCommentForm cardId={cardId} onAdded={handleAdded} />}
    </section>
  )
}
