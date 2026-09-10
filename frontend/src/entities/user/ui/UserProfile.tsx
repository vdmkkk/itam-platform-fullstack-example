import type { UserDetail } from '@/shared/api'
import { Avatar } from '@/shared/ui'
import styles from './UserProfile.module.css'

export function UserProfile({ user }: { user: UserDetail }) {
  return (
    <section className={styles.profile}>
      <Avatar name={user.name} src={user.avatar_url} size={96} />

      <div className={styles.info}>
        <h1 className={styles.name}>
          {user.name}
          {user.is_me && <span className={styles.you}>это вы</span>}
        </h1>
        {user.status && <p className={styles.status}>{user.status}</p>}
        {user.bio && <p className={styles.bio}>{user.bio}</p>}
        {user.telegram && (
          <a href={`https://t.me/${user.telegram}`} target="_blank" rel="noreferrer">
            @{user.telegram}
          </a>
        )}

        <dl className={styles.stats}>
          <div>
            <dt>Карточек</dt>
            <dd>{user.cards_count}</dd>
          </div>
          <div>
            <dt>Комментариев</dt>
            <dd>{user.comments_count}</dd>
          </div>
          <div>
            <dt>Рейтинг</dt>
            <dd>{user.total_score}</dd>
          </div>
        </dl>
      </div>
    </section>
  )
}
