import type { ReactNode } from 'react'
import { Link } from 'react-router'
import type { Comment } from '@/shared/api'
import { routes } from '@/shared/config'
import { formatDateTime } from '@/shared/lib'
import { Avatar } from '@/shared/ui'
import styles from './CommentItem.module.css'

type Props = {
  comment: Comment
  /** Кнопки действий (например, «Удалить») — их передаёт тот, кто рисует список */
  actions?: ReactNode
}

export function CommentItem({ comment, actions }: Props) {
  const edited = comment.updated_at !== comment.created_at

  return (
    <article className={styles.comment}>
      <Avatar name={comment.author.name} src={comment.author.avatar_url} size={36} />
      <div className={styles.body}>
        <header className={styles.header}>
          <Link to={routes.user(comment.author.id)} className={styles.author}>
            {comment.author.name}
          </Link>
          <span className={styles.time}>
            {formatDateTime(comment.created_at)}
            {edited && ' · изменено'}
          </span>
          {actions && <span className={styles.actions}>{actions}</span>}
        </header>
        <p className={styles.text}>{comment.text}</p>
      </div>
    </article>
  )
}
