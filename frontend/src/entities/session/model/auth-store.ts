import { create } from 'zustand'
import { getErrorMessage, type Profile, type ProfileUpdate } from '@/shared/api'
import { getMe, updateMe } from '../api/session-api'

type AuthState = {
  /** Текущий пользователь (GET /api/me) */
  me: Profile | null
  /** Почему не удалось узнать, кто вы. Чаще всего — токен не подошёл */
  error: string | null

  loadMe: () => Promise<void>
  saveProfile: (changes: ProfileUpdate) => Promise<void>
}

// Кто вы — нужно шапке, странице пользователя и форме профиля. Храним это в одном месте
export const useAuthStore = create<AuthState>()((set) => ({
  me: null,
  error: null,

  loadMe: async () => {
    set({ error: null })
    try {
      set({ me: await getMe() })
    } catch (err) {
      set({ error: getErrorMessage(err) })
    }
  },

  saveProfile: async (changes) => {
    set({ me: await updateMe(changes) })
  },
}))
