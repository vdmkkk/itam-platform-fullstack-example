import { Link } from 'react-router'
import { CardDetails, useCardsStore } from '@/entities/card'
import { VoteButtons } from '@/features/vote'
import { routes } from '@/shared/config'
import { Modal } from '@/shared/ui'
import styles from './CardModal.module.css'

type Props = {
  cardId: string
  onClose: () => void
}

export function CardModal({ cardId, onClose }: Props) {
  // Карточку берём из стора: проголосовали — и модалка сразу показывает новый счёт
  const card = useCardsStore((state) => state.cards.find((item) => item.id === cardId))
  if (!card) return null

  return (
    <Modal title={card.title} onClose={onClose}>
      <CardDetails card={card} />
      <footer className={styles.footer}>
        <VoteButtons card={card} />
        <Link to={routes.card(card.id)}>Комментарии и подробности →</Link>
      </footer>
    </Modal>
  )
}
