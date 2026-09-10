import { useState } from 'react'
import styles from './Avatar.module.css'

type Props = {
  name: string
  src?: string | null
  size?: number
}

/** Цвет фона для инициалов: у одного и того же имени он всегда одинаковый */
function colorFor(name: string) {
  let hue = 0
  for (const char of name) hue = (hue * 31 + char.charCodeAt(0)) % 360
  return `hsl(${hue} 55% 55%)`
}

function initialsOf(name: string) {
  return name
    .trim()
    .split(/\s+/)
    .map((word) => word[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()
}

export function Avatar({ name, src, size = 40 }: Props) {
  // Запоминаем ссылку, которая не загрузилась, и вместо неё показываем инициалы
  const [brokenSrc, setBrokenSrc] = useState<string | null>(null)
  const style = { width: size, height: size, fontSize: size * 0.4 }

  if (src && src !== brokenSrc) {
    return <img className={styles.avatar} src={src} alt="" style={style} onError={() => setBrokenSrc(src)} />
  }
  return (
    <span className={styles.avatar} style={{ ...style, background: colorFor(name) }} aria-hidden="true">
      {initialsOf(name)}
    </span>
  )
}
