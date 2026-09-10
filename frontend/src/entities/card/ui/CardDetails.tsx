import { Link } from 'react-router'
import type { Card } from '@/shared/api'
import { routes } from '@/shared/config'
import { cn, formatDateTime, plural } from '@/shared/lib'
import { Avatar } from '@/shared/ui'
import { TypeBadge } from './TypeBadge'
import styles from './CardDetails.module.css'

function progressText(card: Card) {
  if (card.is_accepted) return 'Карточка набрала нужное число голосов и принята.'
  if (card.is_rejected) return 'Карточка набрала слишком много голосов «против» и отклонена.'
  const votes = card.votes_to_accept
  return `До принятия не хватает ${votes} ${plural(votes, ['голоса', 'голосов', 'голосов'])} «за».`
}

/** Всё о карточке, кроме заголовка, голосования и комментариев */
export function CardDetails({ card }: { card: Card }) {
  return (
    <div className={styles.details}>
      <div className={styles.row}>
        <TypeBadge type={card.type} />
        {card.is_accepted && <span className={cn(styles.status, styles.accepted)}>Принято</span>}
        {card.is_rejected && <span className={cn(styles.status, styles.rejected)}>Отклонено</span>}
      </div>

      <div className={styles.row}>
        <Link to={routes.user(card.author.id)} className={styles.author}>
          <Avatar name={card.author.name} src={card.author.avatar_url} size={28} />
          {card.author.name}
        </Link>
        <span className={styles.muted}>{formatDateTime(card.created_at)}</span>
      </div>

      {card.preview && <img className={styles.image} src={card.preview} alt="" />}
      {card.date !== null && <p className={styles.date}>📅 {formatDateTime(card.date)}</p>}
      {card.description && <p className={styles.description}>{card.description}</p>}
      <p className={styles.muted}>{progressText(card)}</p>
    </div>
  )
}
