import { Button } from '../Button/Button'
import styles from './ErrorMessage.module.css'

type Props = {
  message: string
  onRetry?: () => void
}

export function ErrorMessage({ message, onRetry }: Props) {
  return (
    <div className={styles.error} role="alert">
      <p className={styles.text}>{message}</p>
      {onRetry && <Button onClick={onRetry}>Повторить</Button>}
    </div>
  )
}
