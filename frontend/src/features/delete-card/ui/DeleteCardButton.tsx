import { useState } from 'react'
import { useCardsStore } from '@/entities/card'
import { getErrorMessage } from '@/shared/api'
import { Button } from '@/shared/ui'

type Props = {
  cardId: string
  onDeleted: () => void
}

export function DeleteCardButton({ cardId, onDeleted }: Props) {
  const deleteCard = useCardsStore((state) => state.deleteCard)
  const [pending, setPending] = useState(false)

  async function handleClick() {
    if (!window.confirm('Удалить карточку вместе с голосами и комментариями?')) return
    setPending(true)
    try {
      await deleteCard(cardId)
      onDeleted()
    } catch (err) {
      window.alert(getErrorMessage(err))
      setPending(false)
    }
  }

  return (
    <Button variant="danger" onClick={handleClick} disabled={pending}>
      Удалить карточку
    </Button>
  )
}
