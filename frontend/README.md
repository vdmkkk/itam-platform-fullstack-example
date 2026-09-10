# ITAM Board — фронтенд

Учебное React-приложение курса **Frontend (ITAM)**: доска событий, идей и вопросов поверх
[ITAM Board API](../backend/README.md). Это итог уроков 8–15: к концу курса у каждого студента
получается такое же приложение.

- API: `https://courses.salut.uno/example-backend/frontend-itam`
- Swagger: https://courses.salut.uno/example-backend/frontend-itam/docs

## Запуск

Нужен Node.js 22.22 или новее.

1. Скопируйте свой токен курса (страница курса → вкладка «API проекта») и вставьте его в
   константу `COURSE_TOKEN` в `src/shared/api/client.ts`.
2. Запустите:

   ```sh
   cd frontend
   npm install
   npm run dev
   ```

3. Откройте http://localhost:5173.

Входа в приложении нет: API узнаёт вас по токену, который уходит в заголовке `X-Course-Token`
с каждым запросом. Держать токен в коде обычно нельзя, но этот открывает только учебный API.

| Команда | Что делает |
| --- | --- |
| `npm run dev` | Dev-сервер с горячей перезагрузкой |
| `npm run build` | Проверка типов (`tsc`) и сборка в `dist/` |
| `npm run preview` | Запуск собранной версии |
| `npm run lint` | Линтер (oxlint) |
| `npm run api:types` | Заново сгенерировать типы API в `src/shared/api/schema.d.ts` |

Другой адрес API можно задать в `.env.local`: `VITE_API_URL=http://localhost:8000`.

## Что умеет приложение

- Доска из пяти колонок: События, Идеи, Вопросы, Принято, Отклонено. Карточка попадает в
  колонку по полю `column`, которое считает сервер.
- Поиск, «Только мои» и сортировка: сначала новые, старые или популярные.
- Модалка карточки: подробности, голосование «за» и «против» и комментарии. Комментарии
  загружаются сразу, как только модалка открылась; можно написать свой и удалить свой.
  Повторный клик по голосу отменяет его, за свою карточку голосовать нельзя.
- У своей карточки в модалке есть «Редактировать» и «Удалить карточку». «Редактировать» ведёт на
  страницу карточки, и она нужна только для этого: на ней форма редактирования и больше ничего.
- Создание карточки: заголовок, тип, описание, картинка по ссылке, дата.
- Страница пользователя: профиль, счётчики и его карточки (открываются в той же модалке). На своей
  странице можно отредактировать профиль с клиентской и серверной валидацией (например, «Этот email уже занят»).
- В шапке — вы, владелец токена. Если токен не подошёл, вместо страницы будет причина и кнопка
  «Повторить».

## Стек

| Что | Зачем |
| --- | --- |
| Vite 8, TypeScript 6 | Сборка и типы |
| React 19 | Интерфейс |
| React Router 8 | Страницы |
| react-hook-form | Формы и валидация |
| Zustand | Сторы: карточки и текущий пользователь |
| openapi-typescript | Типы API из Swagger (запускается через `npx`, в зависимостях его нет) |
| CSS Modules | Стили лежат рядом с компонентами |
| oxlint | Линтер (его ставит шаблон Vite) |

## Структура: Feature-Sliced Design

```
src/
├── app/        точка входа, роутинг, каркас страниц, глобальные стили
├── pages/      страницы: board, card (редактирование), user, not-found
├── widgets/    крупные блоки страниц: header, board-columns, card-modal (карточка и комментарии)
├── features/   действия пользователя: card-form, vote, filter-cards, add-comment,
│               delete-card, delete-comment, edit-profile
├── entities/   сущности: card, user, comment, session — их API, сторы и отображение
└── shared/     общее без бизнес-логики: api, ui, lib, config
```

Два правила FSD:

1. Слой импортирует только из слоёв ниже: `app` → `pages` → `widgets` → `features` → `entities` → `shared`.
   Соседние слайсы одного слоя друг друга не импортируют — поэтому комментарии лежат внутри
   `widgets/card-modal`, а не отдельным виджетом.
2. В чужой слайс заходим только через его `index.ts` (публичный API): `@/entities/card`, а не
   `@/entities/card/ui/CardPreview`.

Внутри слайса код разложен по сегментам: `ui` (компоненты), `model` (сторы и логика), `api`
(запросы), `lib` (вспомогательное).

## Карта уроков

Приложение — итог уроков 8–15. Для каждого урока: что в нём появляется и где это лежит в коде.
Пометка «промежуточно» — то, что на уроке делаем проще, а позже переделываем.

### 8. TypeScript, npm, Vite

- `npm create vite@latest -- --template react-ts` даёт `package.json`, `vite.config.ts`,
  `tsconfig.*.json` и `.oxlintrc.json`.
- `scripts` и зависимости в `package.json`: `dependencies` против `devDependencies`.
- Первые типы: пропсы и union-типы, например `variant?: 'primary' | 'secondary' | 'danger' | 'ghost'` в `shared/ui/Button`.

### 9. React: JSX, компоненты, props, списки

- Компоненты и props: `shared/ui/Button`, `entities/card/ui/CardPreview`, `entities/card/ui/TypeBadge`.
- Рендеринг массивов и `key`: `widgets/board-columns` раскладывает карточки по колонкам в
  зависимости от `card.column`. Это практика «разместить компоненты в разные колонки по статусу».
- Промежуточно: карточки — моковый массив прямо в коде.

### 10. Состояние: useState, useEffect, иммутабельность

- `useState`: в `pages/board` хранится, какая карточка открыта в модалке и открыта ли форма.
- `useEffect`: `shared/ui/Modal` подписывается на Escape и отписывается в cleanup.
  `widgets/card-modal/ui/CardComments.tsx` загружает комментарии, как только модалка открылась,
  и выбрасывает устаревший ответ через флаг `ignore`.
- Иммутабельность: `setComments((prev) => prev && [...prev, comment])` в `CardComments.tsx`,
  `replaceCard` в `entities/card/model/cards-store.ts`.
- Модалка: `shared/ui/Modal` и `widgets/card-modal` — подробности, голосование и комментарии.
- Промежуточно: голос — локальное состояние карточки, API ещё не подключено.

### 11. Роутинг и архитектура

- `app/App.tsx`: `BrowserRouter`, `Routes`, `Route`. `app/Layout.tsx`: шапка и `Outlet`.
- Страницы `/`, `/cards/:cardId`, `/users/:userId` и `*`; `Link`, `useParams`, `useNavigate`.
  Адреса страниц собраны в `shared/config/routes.ts`.
- Страница карточки открывается из модалки кнопкой «Редактировать» (есть только у своей карточки)
  и нужна только для редактирования. Ещё появляются страница пользователя и компонент новой карточки.
- Раскладываем код по слоям FSD и добавляем алиас `@/` (`vite.config.ts` и `tsconfig.app.json`).

### 12. API в React, кодоген, углублённая типизация

- Swagger как документация: https://courses.salut.uno/example-backend/frontend-itam/docs
- `npm run api:types` генерирует `shared/api/schema.d.ts`, а `shared/api/types.ts` даёт типам
  короткие имена (`Card`, `Profile`...).
- Клиент `shared/api/client.ts`: `fetch`, токен курса в константе `COURSE_TOKEN` и заголовок
  `X-Course-Token` в каждом запросе, `ApiError` с ошибками полей.
- Первый GET — `getCards`, первый POST — `createCard` (`entities/card/api/cards-api.ts`).
- Union-типы из схемы: `CardType`, `CardColumn`, `VoteValue | null`. Ещё `Record<CardType, string>`
  (`entities/card/lib/columns.ts`), статус загрузки `'idle' | 'loading' | 'ready' | 'error'`
  и кортеж в `shared/lib/plural.ts`.
- Промежуточно: `pages/board` грузит карточки сам, через `useState` и `useEffect`.

### 13. Формы

- Управляемое поле (controlled input) и submit: `features/add-comment`.
- `useForm`: `features/card-form` (создание — в модалке на доске, редактирование — на странице
  карточки), `features/edit-profile`.
- Клиентская валидация — правила в `register(...)`: `required`, `maxLength`, `pattern`.
- Серверная валидация — `shared/lib/form-errors.ts`: `errors: [{ field, message }]` от API
  встают под свои поля. Пример — 409 «Этот email уже занят» в форме профиля. Попробовать:
  пробелы в заголовке карточки проходят клиентскую проверку, но сервер ответит «Не может быть пустым».
- Общие ошибки: `ApiError`, `getErrorMessage`, `errors.root.server`.

### 14. useRef, useMemo, useContext

- `useRef`: автофокус на первое поле формы в `features/card-form`. Элемент нужен и нам, и
  react-hook-form, поэтому ref-колбэк отдаёт его обоим.
- `useMemo`: `filterCards` в `pages/board`, `groupByColumn` в `widgets/board-columns`,
  карточки пользователя в `pages/user`.
- `memo`: `CardPreview` не перерисовывается при вводе в поиск. Для этого `onOpen` должен быть
  стабильным: мы передаём сеттер `setOpenCardId`, он не меняется между рендерами.
- Промежуточно: фильтры живут в контексте (пример ниже). На уроке 15 они переезжают в стор.

### 15. Сторы

- Zustand, общий стор карточек `entities/card/model/cards-store.ts`: карточки, статус
  загрузки, фильтры и действия (загрузить, создать, изменить, удалить, проголосовать).
  Доска, модалка, страница карточки и страница пользователя берут данные из него. Комментарии
  живут в модалке, а счётчик 💬 на превью стор обновляет через `changeCommentsCount`.
- Стор авторизации `entities/session/model/auth-store.ts`: кто вы (`GET /api/me`), загрузка и
  сохранение профиля. Страница пользователя узнаёт из него, чья она, а шапка сама обновляется
  после сохранения профиля. Если токен не подошёл, `app/Layout.tsx` показывает ошибку из стора.
- Селекторы: `useCardsStore((state) => state.cards)` подписывает компонент только на нужную часть.
  Из селектора нельзя возвращать новый массив (`state.cards.filter(...)`): это новый результат
  на каждый вызов и бесконечные перерисовки. Поэтому фильтруем в `useMemo`.
- Стор против контекста: контекст передаёт значение вниз по дереву, а стор — это отдельное
  хранилище с действиями. Его можно прочитать и вне React (`useCardsStore.getState()`), и он
  не перерисовывает всех потребителей подряд.

## Промежуточный шаг урока 14: фильтры на контексте

До урока 15 фильтры можно держать в контексте. Провайдер оборачивает доску, а
`features/filter-cards` и `pages/board` читают значение через `useContext`:

```tsx
import { createContext, useContext, useState, type ReactNode } from 'react'

type FiltersValue = {
  filters: CardFilters
  setFilters: (changes: Partial<CardFilters>) => void
}

const FiltersContext = createContext<FiltersValue | null>(null)

export function FiltersProvider({ children }: { children: ReactNode }) {
  const [filters, setAll] = useState(DEFAULT_FILTERS)
  const setFilters = (changes: Partial<CardFilters>) => setAll((prev) => ({ ...prev, ...changes }))
  return <FiltersContext value={{ filters, setFilters }}>{children}</FiltersContext>
}

export function useFilters() {
  const value = useContext(FiltersContext)
  if (!value) throw new Error('useFilters нужно вызывать внутри FiltersProvider')
  return value
}
```

На уроке 15 `filters` и `setFilters` переезжают в `useCardsStore`, провайдер удаляем, а
`useFilters()` заменяем на селекторы стора. Заодно фильтры перестают сбрасываться при уходе с доски.
