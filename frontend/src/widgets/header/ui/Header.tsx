import { Link } from 'react-router'
import { useAuthStore } from '@/entities/session'
import { routes } from '@/shared/config'
import { Avatar } from '@/shared/ui'
import styles from './Header.module.css'

export function Header() {
  const me = useAuthStore((state) => state.me)

  return (
    <header className={styles.header}>
      <div className={styles.inner}>
        <Link to={routes.board()} className={styles.logo}>
          <img src="/favicon.svg" alt="" width={28} height={28} />
          ITAM Board
        </Link>

        {me && (
          <Link to={routes.user(me.id)} className={styles.me}>
            <Avatar name={me.name} src={me.avatar_url} size={32} />
            <span className={styles.name}>{me.name}</span>
          </Link>
        )}
      </div>
    </header>
  )
}
