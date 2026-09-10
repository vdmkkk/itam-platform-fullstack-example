import { useEffect } from 'react'
import { Outlet } from 'react-router'
import { useAuthStore } from '@/entities/session'
import { Header } from '@/widgets/header'
import styles from './Layout.module.css'

/** Общий каркас страниц: шапка сверху, текущая страница (Outlet) под ней */
export function Layout() {
  const me = useAuthStore((state) => state.me)
  const loadMe = useAuthStore((state) => state.loadMe)

  // Токен сохранён с прошлого раза, а профиль — нет: загрузим его
  useEffect(() => {
    if (!me) loadMe()
  }, [me, loadMe])

  return (
    <>
      <Header />
      <main className={styles.main}>
        <Outlet />
      </main>
    </>
  )
}
