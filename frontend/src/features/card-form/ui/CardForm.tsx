import { useEffect, useRef } from 'react'
import { useForm, useWatch } from 'react-hook-form'
import { CARD_TYPES, TYPE_LABELS, useCardsStore } from '@/entities/card'
import type { Card, CardCreate, CardType } from '@/shared/api'
import { showServerErrors, toDateTimeLocal, toUnix } from '@/shared/lib'
import { Button, Field } from '@/shared/ui'
import styles from './CardForm.module.css'

type FormValues = {
  title: string
  type: CardType
  description: string
  preview: string
  /** Значение <input type="datetime-local">; пустая строка — без даты */
  date: string
}

const FIELDS = ['title', 'type', 'description', 'preview', 'date'] as const
const IMAGE_LINK = /^(https?:\/\/|data:image\/)/

function toFormValues(card?: Card): FormValues {
  return {
    title: card?.title ?? '',
    type: card?.type ?? 'idea',
    description: card?.description ?? '',
    preview: card?.preview ?? '',
    date: card?.date ? toDateTimeLocal(card.date) : '',
  }
}

// В форме всё — строки, а API ждёт null вместо пустых полей и Unix-время вместо даты
function toRequestBody(values: FormValues): CardCreate {
  return {
    title: values.title.trim(),
    type: values.type,
    description: values.description.trim() || null,
    preview: values.preview.trim() || null,
    date: values.date ? toUnix(values.date) : null,
  }
}

type Props = {
  /** Карточка, которую редактируем. Без неё форма создаёт новую */
  card?: Card
  onDone: (card: Card) => void
  onCancel: () => void
}

export function CardForm({ card, onDone, onCancel }: Props) {
  const createCard = useCardsStore((state) => state.createCard)
  const updateCard = useCardsStore((state) => state.updateCard)
  const {
    register,
    handleSubmit,
    setError,
    control,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ defaultValues: toFormValues(card) })

  // Автофокус на первое поле. Элемент нужен и нам, и react-hook-form, поэтому отдаём его обоим
  const titleRef = useRef<HTMLInputElement | null>(null)
  const titleField = register('title', {
    required: 'Введите заголовок',
    maxLength: { value: 120, message: 'Не длиннее 120 символов' },
  })
  useEffect(() => {
    titleRef.current?.focus()
  }, [])

  async function submit(values: FormValues) {
    try {
      const body = toRequestBody(values)
      const saved = card ? await updateCard(card.id, body) : await createCard(body)
      onDone(saved)
    } catch (err) {
      // Ошибки сервера встают под поля так же, как ошибки клиентской валидации
      showServerErrors(err, setError, FIELDS)
    }
  }

  // Следим за полем, чтобы сразу показать картинку по введённой ссылке
  const preview = useWatch({ control, name: 'preview' })
  const submitLabel = card ? 'Сохранить' : 'Создать карточку'

  return (
    <form className={styles.form} onSubmit={handleSubmit(submit)} noValidate>
      <Field label="Заголовок" error={errors.title?.message}>
        <input
          {...titleField}
          ref={(element) => {
            titleField.ref(element)
            titleRef.current = element
          }}
          placeholder="Например, «Сходить на хакатон»"
        />
      </Field>

      <Field label="Тип" error={errors.type?.message}>
        <select {...register('type')}>
          {CARD_TYPES.map((type) => (
            <option key={type} value={type}>
              {TYPE_LABELS[type]}
            </option>
          ))}
        </select>
      </Field>

      <Field label="Описание" error={errors.description?.message}>
        <textarea
          {...register('description', { maxLength: { value: 5000, message: 'Не длиннее 5000 символов' } })}
          rows={4}
        />
      </Field>

      <Field label="Картинка" error={errors.preview?.message} hint="Ссылка на картинку, необязательно">
        <input
          {...register('preview', {
            pattern: { value: IMAGE_LINK, message: 'Ссылка должна начинаться с http:// или https://' },
          })}
          placeholder="https://..."
        />
      </Field>
      {IMAGE_LINK.test(preview) && <img className={styles.preview} src={preview} alt="" />}

      <Field label="Дата" error={errors.date?.message} hint="Необязательно, удобно для событий">
        <input type="datetime-local" {...register('date')} />
      </Field>

      {errors.root?.server && <p className={styles.error}>{errors.root.server.message}</p>}

      <div className={styles.actions}>
        <Button onClick={onCancel}>Отмена</Button>
        <Button type="submit" variant="primary" disabled={isSubmitting}>
          {isSubmitting ? 'Сохраняем…' : submitLabel}
        </Button>
      </div>
    </form>
  )
}
