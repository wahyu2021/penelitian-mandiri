import { z } from 'zod'
import { apiGet } from '@/lib/api/client'

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

export function getSearchFilters(): Promise<SearchFilters> {
  return apiGet('/api/v1/search/filters', filtersSchema)
}

export function getSearchResults(params: string): Promise<SearchResults> {
  return apiGet(`/api/v1/search?${params}`, resultSchema)
}
