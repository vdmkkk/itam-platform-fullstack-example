import { useForm, useWatch } from 'react-hook-form'
import { useAuthStore } from '@/entities/session'
import type { Profile } from '@/shared/api'
import { showServerErrors } from '@/shared/lib'
import { Avatar, Button, Field } from '@/shared/ui'
import styles from './ProfileForm.module.css'

type FormValues = {
  name: string
  email: string
  avatar_url: string
  status: string
  bio: string
  telegram: string
}

const FIELDS = ['name', 'email', 'avatar_url', 'status', 'bio', 'telegram'] as const

type Props = {
  profile: Profile
  onDone: () => void
  onCancel: () => void
}

export function ProfileForm({ profile, onDone, onCancel }: Props) {
  const saveProfile = useAuthStore((state) => state.saveProfile)
  const {
    register,
    handleSubmit,
    setError,
    control,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    defaultValues: {
      name: profile.name,
      email: profile.email ?? '',
      avatar_url: profile.avatar_url ?? '',
      status: profile.status ?? '',
      bio: profile.bio ?? '',
      telegram: profile.telegram ?? '',
    },
  })

  async function submit(values: FormValues) {
    try {
      // Пустые поля отправляем как null — сервер их очистит
      await saveProfile({
        name: values.name.trim(),
        email: values.email.trim() || null,
        avatar_url: values.avatar_url.trim() || null,
        status: values.status.trim() || null,
        bio: values.bio.trim() || null,
        telegram: values.telegram.trim() || null,
      })
      onDone()
    } catch (err) {
      // Например, 409 «Этот email уже занят» встанет прямо под полем email
      showServerErrors(err, setError, FIELDS)
    }
  }

  // Следим за полем, чтобы аватар слева сразу менялся по введённой ссылке
  const avatarUrl = useWatch({ control, name: 'avatar_url' })

  return (
    <form className={styles.form} onSubmit={handleSubmit(submit)} noValidate>
      <div className={styles.avatarRow}>
        <Avatar name={profile.name} src={avatarUrl} size={64} />
        <Field label="Аватар" error={errors.avatar_url?.message} hint="Ссылка на картинку">
          <input
            {...register('avatar_url', {
              pattern: { value: /^(https?:\/\/|data:image\/)/, message: 'Ссылка должна начинаться с http:// или https://' },
            })}
            placeholder="https://..."
          />
        </Field>
      </div>

      <Field label="Имя" error={errors.name?.message}>
        <input
          {...register('name', {
            required: 'Введите имя',
            maxLength: { value: 80, message: 'Не длиннее 80 символов' },
          })}
        />
      </Field>

      <Field label="Email" error={errors.email?.message} hint="Виден только вам">
        <input
          type="email"
          {...register('email', {
            pattern: { value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/, message: 'Похоже, это не email' },
          })}
        />
      </Field>

      <Field label="Статус" error={errors.status?.message}>
        <input
          {...register('status', { maxLength: { value: 100, message: 'Не длиннее 100 символов' } })}
          placeholder="Например, «Ищу команду на хакатон»"
        />
      </Field>

      <Field label="О себе" error={errors.bio?.message}>
        <textarea
          {...register('bio', { maxLength: { value: 1000, message: 'Не длиннее 1000 символов' } })}
          rows={3}
        />
      </Field>

      <Field label="Telegram" error={errors.telegram?.message}>
        <input
          {...register('telegram', {
            pattern: { value: /^@?[A-Za-z0-9_]{5,32}$/, message: 'От 5 до 32 латинских букв, цифр или _' },
          })}
          placeholder="@username"
        />
      </Field>

      {errors.root?.server && <p className={styles.error}>{errors.root.server.message}</p>}

      <div className={styles.actions}>
        <Button onClick={onCancel}>Отмена</Button>
        <Button type="submit" variant="primary" disabled={isSubmitting}>
          {isSubmitting ? 'Сохраняем…' : 'Сохранить'}
        </Button>
      </div>
    </form>
  )
}
