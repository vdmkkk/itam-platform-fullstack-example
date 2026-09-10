// Типы данных API. Мы их не пишем руками: `npm run api:types` генерирует schema.d.ts
// из OpenAPI-схемы бэкенда, а здесь мы только даём им короткие имена.
import type { components } from './schema'

type Schemas = components['schemas']

export type Card = Schemas['Card']
export type CardCreate = Schemas['CardCreate']
export type CardUpdate = Schemas['CardUpdate']
export type CardType = Schemas['CardType']
export type CardColumn = Schemas['CardColumn']
export type CardSort = Schemas['CardSort']
export type VoteValue = Schemas['VoteValue']
export type Comment = Schemas['Comment']
export type User = Schemas['User']
export type UserDetail = Schemas['UserDetail']
export type Profile = Schemas['Profile']
export type ProfileUpdate = Schemas['ProfileUpdate']
export type FieldError = Schemas['FieldError']
