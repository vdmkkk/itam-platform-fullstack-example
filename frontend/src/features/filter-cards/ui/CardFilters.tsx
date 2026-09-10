import { useCardsStore } from '@/entities/card'
import type { CardSort } from '@/shared/api'
import styles from './CardFilters.module.css'

export function CardFilters() {
  // Селекторы: компонент перерисуется, только когда поменяются filters, а не весь стор
  const filters = useCardsStore((state) => state.filters)
  const setFilters = useCardsStore((state) => state.setFilters)

  return (
    <div className={styles.filters}>
      <input
        type="search"
        className={styles.search}
        value={filters.search}
        onChange={(event) => setFilters({ search: event.target.value })}
        placeholder="Поиск по карточкам"
        aria-label="Поиск по карточкам"
      />
      <select
        className={styles.sort}
        value={filters.sort}
        onChange={(event) => setFilters({ sort: event.target.value as CardSort })}
        aria-label="Сортировка"
      >
        <option value="new">Сначала новые</option>
        <option value="old">Сначала старые</option>
        <option value="top">Сначала популярные</option>
      </select>
      <label className={styles.mine}>
        <input
          type="checkbox"
          checked={filters.onlyMine}
          onChange={(event) => setFilters({ onlyMine: event.target.checked })}
        />
        Только мои
      </label>
    </div>
  )
}
