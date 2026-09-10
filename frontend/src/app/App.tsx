import { BrowserRouter, Route, Routes } from 'react-router'
import { useAuthStore } from '@/entities/session'
import { BoardPage } from '@/pages/board'
import { CardPage } from '@/pages/card'
import { LoginPage } from '@/pages/login'
import { NotFoundPage } from '@/pages/not-found'
import { UserPage } from '@/pages/user'
import { Layout } from './Layout'

export function App() {
  const token = useAuthStore((state) => state.token)

  // Без токена API нам ничего не отдаст — сначала просим войти
  if (!token) return <LoginPage />

  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<BoardPage />} />
          <Route path="cards/:cardId" element={<CardPage />} />
          <Route path="users/:userId" element={<UserPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
