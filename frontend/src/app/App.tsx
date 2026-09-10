import { BrowserRouter, Route, Routes } from 'react-router'
import { BoardPage } from '@/pages/board'
import { CardPage } from '@/pages/card'
import { NotFoundPage } from '@/pages/not-found'
import { UserPage } from '@/pages/user'
import { Layout } from './Layout'

export function App() {
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
