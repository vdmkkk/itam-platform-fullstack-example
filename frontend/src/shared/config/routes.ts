// Адреса страниц в одном месте: если путь поменяется, править придётся только здесь
export const routes = {
  board: () => '/',
  card: (cardId: string) => `/cards/${cardId}`,
  user: (userId: string) => `/users/${userId}`,
}
