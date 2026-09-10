/** Склеивает CSS-классы, пропуская пустые: cn('card', isActive && 'active') */
export function cn(...classes: (string | false | null | undefined)[]) {
  return classes.filter(Boolean).join(' ')
}
