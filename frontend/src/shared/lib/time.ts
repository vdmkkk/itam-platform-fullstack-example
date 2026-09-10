// API присылает время как Unix-время в секундах, а Date в JS считает миллисекундами

/** 1791648000 → «10 окт. 2026 г., 19:00» */
export function formatDateTime(unix: number) {
  return new Date(unix * 1000).toLocaleString('ru-RU', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** Значение <input type="datetime-local"> («2026-10-10T19:00») → Unix-время */
export function toUnix(dateTimeLocal: string) {
  return Math.floor(new Date(dateTimeLocal).getTime() / 1000)
}

/** Unix-время → значение для <input type="datetime-local"> (в часовом поясе браузера) */
export function toDateTimeLocal(unix: number) {
  const date = new Date(unix * 1000)
  const pad = (value: number) => String(value).padStart(2, '0')
  const day = `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
  return `${day}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}
