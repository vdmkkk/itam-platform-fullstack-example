import { useEffect, useRef, useState, type SubmitEvent } from 'react'
import { useAuthStore } from '@/entities/session'
import { getErrorMessage } from '@/shared/api'
import { Button, Field } from '@/shared/ui'
import styles from './LoginForm.module.css'

// Управляемая форма (controlled input): значение поля хранится в состоянии React
export function LoginForm() {
  const login = useAuthStore((state) => state.login)
  const [token, setToken] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)

  // useRef даёт доступ к самому DOM-элементу — например, чтобы поставить в него курсор
  const inputRef = useRef<HTMLInputElement>(null)
  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  async function handleSubmit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault()
    setPending(true)
    setError(null)
    try {
      await login(token.trim())
      // Дальше App сам покажет доску: в сторе появился токен
    } catch (err) {
      setError(getErrorMessage(err))
      setPending(false)
    }
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <Field
        label="Токен курса"
        error={error ?? undefined}
        hint="Страница курса → вкладка «API проекта» → «Копировать»"
      >
        <input
          ref={inputRef}
          value={token}
          onChange={(event) => setToken(event.target.value)}
          placeholder="exb_..."
          autoComplete="off"
          spellCheck={false}
        />
      </Field>
      <Button type="submit" variant="primary" disabled={pending || !token.trim()}>
        {pending ? 'Проверяем…' : 'Войти'}
      </Button>
    </form>
  )
}
