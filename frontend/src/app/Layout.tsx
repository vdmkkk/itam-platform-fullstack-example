import { useEffect } from 'react'
import { Outlet } from 'react-router'
import { useAuthStore } from '@/entities/session'
import { ErrorMessage } from '@/shared/ui'
import { Header } from '@/widgets/header'
import styles from './Layout.module.css'

/** Общий каркас страниц: шапка сверху, текущая страница (Outlet) под ней */
export function Layout() {
  const error = useAuthStore((state) => state.error)
  const loadMe = useAuthStore((state) => state.loadMe)

  // Кто вы — узнаём один раз при запуске приложения
  useEffect(() => {
    loadMe()
  }, [loadMe])

  return (
    <>
      <Header />
      <main className={styles.main}>
        {/* Если токен не подошёл, API ничего не отдаст — вместо страницы покажем причину */}
        {error ? <ErrorMessage message={error} onRetry={loadMe} /> : <Outlet />}
      </main>
    </>
  )
}
