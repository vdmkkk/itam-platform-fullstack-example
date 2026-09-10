import { useAuthStore } from '@/entities/session'
import { LoginForm } from '@/features/login'
import styles from './LoginPage.module.css'

export function LoginPage() {
  // Если нас «разлогинило» (токен сбросили), стор расскажет почему
  const reason = useAuthStore((state) => state.error)

  return (
    <main className={styles.page}>
      <div className={styles.card}>
        <img src="/favicon.svg" alt="" width={48} height={48} />
        <h1 className={styles.title}>ITAM Board</h1>
        <p className={styles.text}>Доска событий, идей и вопросов курса. Чтобы войти, вставьте свой токен курса.</p>
        {reason && <p className={styles.reason}>{reason}</p>}
        <LoginForm />
      </div>
    </main>
  )
}
