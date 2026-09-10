import type { ComponentProps } from 'react'
import { cn } from '@/shared/lib'
import styles from './Button.module.css'

type Props = ComponentProps<'button'> & {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost'
}

// Все остальные пропсы (onClick, disabled, children...) передаём обычной кнопке как есть
export function Button({ variant = 'secondary', type = 'button', className, ...props }: Props) {
  return <button type={type} className={cn(styles.button, styles[variant], className)} {...props} />
}
