import type { FieldValues, Path, UseFormSetError } from 'react-hook-form'
import { ApiError, getErrorMessage } from '@/shared/api'

/**
 * Показывает ошибку сервера в форме react-hook-form.
 * Ошибки полей (`errors: [{ field, message }]`) встают под свои поля — так же,
 * как ошибки клиентской валидации. Всё остальное — общим сообщением в errors.root.server.
 */
export function showServerErrors<T extends FieldValues>(
  error: unknown,
  setError: UseFormSetError<T>,
  fields: readonly Path<T>[],
) {
  const fieldErrors = error instanceof ApiError ? error.fieldErrors : []
  const known = fieldErrors.filter((item) => fields.includes(item.field as Path<T>))

  for (const item of known) {
    setError(item.field as Path<T>, { type: 'server', message: item.message })
  }
  if (known.length === 0) {
    setError('root.server', { type: 'server', message: getErrorMessage(error) })
  }
}
