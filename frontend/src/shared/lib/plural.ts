/** Русское множественное число: plural(5, ['голос', 'голоса', 'голосов']) → 'голосов' */
export function plural(count: number, [one, few, many]: [string, string, string]) {
  const tens = count % 100
  const units = count % 10
  if (units === 1 && tens !== 11) return one
  if (units >= 2 && units <= 4 && (tens < 12 || tens > 14)) return few
  return many
}
