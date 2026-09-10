import { useState } from 'react'
import { deleteComment } from '@/entities/comment'
import { getErrorMessage } from '@/shared/api'
import { Button } from '@/shared/ui'

type Props = {
  commentId: string
  onDeleted: () => void
}

export function DeleteCommentButton({ commentId, onDeleted }: Props) {
  const [pending, setPending] = useState(false)

  async function handleClick() {
    if (!window.confirm('Удалить комментарий?')) return
    setPending(true)
    try {
      await deleteComment(commentId)
      onDeleted()
    } catch (err) {
      window.alert(getErrorMessage(err))
      setPending(false)
    }
  }

  return (
    <Button variant="ghost" onClick={handleClick} disabled={pending}>
      Удалить
    </Button>
  )
}
