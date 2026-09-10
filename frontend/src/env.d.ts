// Переменные окружения, которые Vite отдаёт в браузер (только с префиксом VITE_)
interface ImportMetaEnv {
  /** Адрес API. По умолчанию — сервер курса. Переопределить можно в `.env.local`. */
  readonly VITE_API_URL?: string
}
