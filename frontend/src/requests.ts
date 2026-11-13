import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { FormEvent } from 'react'
import { api, ApiError } from './api'
import type { Session } from './api'

export const useSession = () => useQuery({ queryKey: ['session'], queryFn: () => api<Session>('session/') })
export const formData = (event: FormEvent<HTMLFormElement>) => {
  event.preventDefault()
  return new FormData(event.currentTarget)
}

export function useWrite<Result = unknown>() {
  const session = useSession()
  const cache = useQueryClient()
  return useMutation({
    mutationFn: async ({ path, method = 'POST', body }: { path: string; method?: string; body?: FormData | Record<string, unknown> }) => {
      const headers = new Headers({ 'X-CSRFToken': session.data?.csrf_token ?? '' })
      if (body && !(body instanceof FormData)) headers.set('Content-Type', 'application/json')
      return api<Result>(path, { method, headers, body: body instanceof FormData ? body : body && JSON.stringify(body) })
    },
    onSuccess: () => cache.invalidateQueries({ predicate: query => query.queryKey[0] !== 'session' }),
    onError: error => {
      if (error instanceof ApiError && error.status === 403) {
        void cache.invalidateQueries({ queryKey: ['session'] })
      }
    },
  })
}
