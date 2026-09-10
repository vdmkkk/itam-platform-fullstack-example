import { Link } from 'react-router'
import { routes } from '@/shared/config'
import styles from './NotFoundPage.module.css'

export function NotFoundPage() {
  return (
    <div className={styles.page}>
      <h1>Страница не найдена</h1>
      <p className={styles.text}>Такой страницы нет. Возможно, ссылка устарела.</p>
      <Link to={routes.board()}>← К доске</Link>
    </div>
  )
}
