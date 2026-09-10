import { useState } from 'react'
import { useCardsStore } from '@/entities/card'
import { getErrorMessage, type Card, type VoteValue } from '@/shared/api'
import { cn } from '@/shared/lib'
import styles from './VoteButtons.module.css'

type Props = {
  card: Card
}

export function VoteButtons({ card }: Props) {
  const vote = useCardsStore((state) => state.vote)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleVote(value: VoteValue) {
    setPending(true)
    setError(null)
    try {
      // Повторный клик по своему голосу отменяет его. Стор заменит карточку, и новый счёт увидят все
      await vote(card.id, card.my_vote === value ? null : value)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setPending(false)
    }
  }

  const disabled = pending || card.is_mine

  return (
    <div className={styles.votes}>
      <button
        type="button"
        className={cn(styles.button, card.my_vote === 'up' && styles.up)}
        onClick={() => handleVote('up')}
        disabled={disabled}
        aria-pressed={card.my_vote === 'up'}
        title="За"
      >
        ▲ {card.upvotes}
      </button>
      <span className={styles.score} title="Счёт">
        {card.score}
      </span>
      <button
        type="button"
        className={cn(styles.button, card.my_vote === 'down' && styles.down)}
        onClick={() => handleVote('down')}
        disabled={disabled}
        aria-pressed={card.my_vote === 'down'}
        title="Против"
      >
        ▼ {card.downvotes}
      </button>
      {card.is_mine && <span className={styles.hint}>За свою карточку голосовать нельзя</span>}
      {error && <span className={styles.error}>{error}</span>}
    </div>
  )
}
