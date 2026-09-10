import styles from './Loader.module.css'

export function Loader({ text = 'Загружаем…' }: { text?: string }) {
  return (
    <div className={styles.loader} role="status">
      <span className={styles.spinner} />
      {text}
    </div>
  )
}
