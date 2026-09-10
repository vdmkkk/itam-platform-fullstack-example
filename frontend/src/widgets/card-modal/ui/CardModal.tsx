import { useNavigate } from 'react-router'
import { CardDetails, useCardsStore } from '@/entities/card'
import { DeleteCardButton } from '@/features/delete-card'
import { VoteButtons } from '@/features/vote'
import { routes } from '@/shared/config'
import { Button, Modal } from '@/shared/ui'
import { CardComments } from './CardComments'
import styles from './CardModal.module.css'

type Props = {
  cardId: string
  onClose: () => void
}

export function CardModal({ cardId, onClose }: Props) {
  const navigate = useNavigate()
  // Карточку берём из стора: проголосовали — и модалка сразу показывает новый счёт
  const card = useCardsStore((state) => state.cards.find((item) => item.id === cardId))
  if (!card) return null

  return (
    <Modal title={card.title} onClose={onClose}>
      <CardDetails card={card} />
      <footer className={styles.footer}>
        <VoteButtons card={card} />
        {card.is_mine && (
          <div className={styles.owner}>
            {/* Страница карточки — только для редактирования */}
            <Button onClick={() => navigate(routes.card(card.id))}>Редактировать</Button>
            <DeleteCardButton cardId={card.id} onDeleted={onClose} />
          </div>
        )}
      </footer>
      <CardComments cardId={card.id} />
    </Modal>
  )
}
