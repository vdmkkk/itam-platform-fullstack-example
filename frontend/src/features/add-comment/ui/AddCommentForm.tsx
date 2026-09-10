import { useState, type SubmitEvent } from 'react'
import { addComment } from '@/entities/comment'
import { getErrorMessage, type Comment } from '@/shared/api'
import { Button } from '@/shared/ui'
import styles from './AddCommentForm.module.css'

type Props = {
  cardId: string
  onAdded: (comment: Comment) => void
}

export function AddCommentForm({ cardId, onAdded }: Props) {
  const [text, setText] = useState('')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault()
    setPending(true)
    setError(null)
    try {
      const comment = await addComment(cardId, text.trim())
      onAdded(comment)
      setText('')
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setPending(false)
    }
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <textarea
        value={text}
        onChange={(event) => setText(event.target.value)}
        placeholder="Написать комментарий…"
        aria-label="Комментарий"
        maxLength={2000}
        rows={3}
      />
      {error && <p className={styles.error}>{error}</p>}
      <Button type="submit" variant="primary" disabled={pending || !text.trim()}>
        {pending ? 'Отправляем…' : 'Отправить'}
      </Button>
    </form>
  )
}
