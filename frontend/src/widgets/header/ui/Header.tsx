import { Link, useNavigate } from 'react-router'
import { useCardsStore } from '@/entities/card'
import { useAuthStore } from '@/entities/session'
import { routes } from '@/shared/config'
import { Avatar, Button } from '@/shared/ui'
import styles from './Header.module.css'

export function Header() {
  const me = useAuthStore((state) => state.me)
  const logout = useAuthStore((state) => state.logout)
  const resetCards = useCardsStore((state) => state.reset)
  const navigate = useNavigate()

  function handleLogout() {
    // Следующий пользователь начнёт с доски, а не с чужой страницы
    navigate(routes.board())
    logout()
    // Карточки загружены от имени прошлого пользователя (my_vote, is_mine) — забываем их
    resetCards()
  }

  return (
    <header className={styles.header}>
      <div className={styles.inner}>
        <Link to={routes.board()} className={styles.logo}>
          <img src="/favicon.svg" alt="" width={28} height={28} />
          ITAM Board
        </Link>

        <nav className={styles.nav}>
          {me && (
            <Link to={routes.user(me.id)} className={styles.me}>
              <Avatar name={me.name} src={me.avatar_url} size={32} />
              <span className={styles.name}>{me.name}</span>
            </Link>
          )}
          <Button variant="ghost" onClick={handleLogout}>
            Выйти
          </Button>
        </nav>
      </div>
    </header>
  )
}
