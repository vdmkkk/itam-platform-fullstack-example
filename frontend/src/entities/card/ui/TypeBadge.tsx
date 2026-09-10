import type { CardType } from '@/shared/api'
import { cn } from '@/shared/lib'
import { TYPE_LABELS } from '../lib/columns'
import styles from './TypeBadge.module.css'

export function TypeBadge({ type }: { type: CardType }) {
  return <span className={cn(styles.badge, styles[type])}>{TYPE_LABELS[type]}</span>
}
