import { z } from 'zod'
import { readResponse } from '@/lib/api/session'

const methodSchema = z.object({ name: z.string(), label: z.string() })
const filtersSchema = z.object({
  data: z.object({
    opds: z.array(z.object({ id: z.number().int().positive(), name: z.string() })),
    default_method: z.string(),
    methods: z.array(methodSchema),
  }),
})

const resultSchema = z.object({
  data: z.object({
    query: z.string(),
    method: z.string(),
    items: z.array(
      z.object({
        id: z.number().int().positive(),
        summary_raw: z.string().nullable(),
        opd_name: z.string().nullable(),
        year: z.number().int().nullable(),
        spm_number: z.string().nullable(),
        file_number: z.string().nullable(),
        has_document: z.boolean(),
        score: z.number(),
      }),
    ),
    pagination: z.object({
      limit: z.number().int().positive(),
      offset: z.number().int().nonnegative(),
      total: z.number().int().nonnegative(),
    }),
  }),
})

export type SearchFilters = z.infer<typeof filtersSchema>['data']
export type SearchResults = z.infer<typeof resultSchema>['data']

export async function getSearchFilters(): Promise<SearchFilters> {
  const response = await fetch('/api/v1/search/filters', {
    credentials: 'same-origin',
    cache: 'no-store',
  })
  return filtersSchema.parse(await readResponse(response)).data
}

export async function getSearchResults(params: string): Promise<SearchResults> {
  const response = await fetch(`/api/v1/search?${params}`, {
    credentials: 'same-origin',
    cache: 'no-store',
  })
  return resultSchema.parse(await readResponse(response)).data
}
