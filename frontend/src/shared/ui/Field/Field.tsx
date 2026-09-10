import type { ReactNode } from 'react'
import styles from './Field.module.css'

type Props = {
  label: string
  error?: string
  hint?: string
  children: ReactNode
}

/** Подпись, поле ввода и под ним ошибка (или подсказка, если ошибки нет) */
export function Field({ label, error, hint, children }: Props) {
  return (
    <label className={styles.field}>
      <span className={styles.label}>{label}</span>
      {children}
      {error && <span className={styles.error}>{error}</span>}
      {!error && hint && <span className={styles.hint}>{hint}</span>}
    </label>
  )
}
