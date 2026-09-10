import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { ApiError, setTokenGetter, type Profile, type ProfileUpdate } from '@/shared/api'
import { getMe, updateMe } from '../api/session-api'

type AuthState = {
  /** Токен курса. Хранится в localStorage, чтобы не вводить его при каждом запуске */
  token: string | null
  /** Текущий пользователь (GET /api/me) */
  me: Profile | null
  /** Почему пришлось войти заново — покажем на странице входа */
  error: string | null

  login: (token: string) => Promise<void>
  loadMe: () => Promise<void>
  saveProfile: (changes: ProfileUpdate) => Promise<void>
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      me: null,
      error: null,

      login: async (token) => {
        // Сначала проверяем токен, и только потом сохраняем: неверный в стор не попадёт
        const me = await getMe(token)
        set({ token, me, error: null })
      },

      loadMe: async () => {
        try {
          set({ me: await getMe() })
        } catch (err) {
          // 401 — токен сбросили на странице курса: просим войти заново
          if (err instanceof ApiError && err.status === 401) {
            set({ token: null, me: null, error: err.message })
          }
        }
      },

      saveProfile: async (changes) => {
        set({ me: await updateMe(changes) })
      },

      logout: () => set({ token: null, me: null, error: null }),
    }),
    {
      name: 'itam-board-auth',
      // В localStorage кладём только токен, а профиль каждый раз берём свежий с сервера
      partialize: (state) => ({ token: state.token }),
    },
  ),
)

// Клиент API берёт токен отсюда перед каждым запросом
setTokenGetter(() => useAuthStore.getState().token)
