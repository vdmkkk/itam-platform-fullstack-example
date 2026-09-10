import { CommentItem } from '@/entities/comment'
import { AddCommentForm } from '@/features/add-comment'
import { DeleteCommentButton } from '@/features/delete-comment'
import type { Comment } from '@/shared/api'
import styles from './CardComments.module.css'

type Props = {
  cardId: string
  comments: Comment[]
  /** Новый список комментариев (исходный массив мы не меняем) */
  onChange: (comments: Comment[]) => void
}

export function CardComments({ cardId, comments, onChange }: Props) {
  function handleDeleted(commentId: string) {
    onChange(comments.filter((comment) => comment.id !== commentId))
  }

  return (
    <section className={styles.section}>
      <h2 className={styles.title}>Комментарии · {comments.length}</h2>

      {comments.length === 0 ? (
        <p className={styles.empty}>Пока никто не написал. Будьте первым!</p>
      ) : (
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
      )}

      <AddCommentForm cardId={cardId} onAdded={(comment) => onChange([...comments, comment])} />
    </section>
  )
}
