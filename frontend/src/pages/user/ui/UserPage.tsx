import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router'
import { CardPreview, useCardsStore } from '@/entities/card'
import { useAuthStore } from '@/entities/session'
import { getUser, UserProfile } from '@/entities/user'
import { ProfileForm } from '@/features/edit-profile'
import { getErrorMessage, type UserDetail } from '@/shared/api'
import { routes } from '@/shared/config'
import { Button, ErrorMessage, Loader } from '@/shared/ui'
import { CardModal } from '@/widgets/card-modal'
import styles from './UserPage.module.css'

export function UserPage() {
  const { userId = '' } = useParams()

  // Кто я — берём из стора авторизации, а не запрашиваем заново
  const me = useAuthStore((state) => state.me)
  const cards = useCardsStore((state) => state.cards)
  const cardsStatus = useCardsStore((state) => state.status)
  const loadCards = useCardsStore((state) => state.loadCards)

  const [user, setUser] = useState<UserDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isEditing, setIsEditing] = useState(false)
  const [openCardId, setOpenCardId] = useState<string | null>(null)

  const isMe = me?.id === userId

  // `me` в зависимостях: после сохранения профиля стор обновит me, и страница перезагрузится
  useEffect(() => {
    let ignore = false
    getUser(userId)
      .then((data) => {
        if (!ignore) setUser(data)
      })
      .catch((err) => {
        if (!ignore) setError(getErrorMessage(err))
      })
    return () => {
      ignore = true
    }
  }, [userId, me])

  // Если пришли сюда не с доски, карточек в сторе ещё нет — загрузим
  useEffect(() => {
    if (cardsStatus === 'idle') loadCards()
  }, [cardsStatus, loadCards])

  const userCards = useMemo(() => cards.filter((card) => card.author.id === userId), [cards, userId])

  if (!user) {
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

      <UserProfile user={user} />

      {isMe && me && isEditing && (
        <ProfileForm profile={me} onDone={() => setIsEditing(false)} onCancel={() => setIsEditing(false)} />
      )}
      {isMe && !isEditing && (
        <Button className={styles.edit} onClick={() => setIsEditing(true)}>
          Редактировать профиль
        </Button>
      )}

      <section className={styles.cards}>
        <h2 className={styles.title}>Карточки · {userCards.length}</h2>
        {userCards.length === 0 ? (
          <p className={styles.empty}>Здесь пока пусто.</p>
        ) : (
          <div className={styles.grid}>
            {userCards.map((card) => (
              <CardPreview key={card.id} card={card} onOpen={setOpenCardId} />
            ))}
          </div>
        )}
      </section>

      {/* Карточка открывается в той же модалке, что и на доске */}
      {openCardId && <CardModal cardId={openCardId} onClose={() => setOpenCardId(null)} />}
    </div>
  )
}
