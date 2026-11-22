import { z } from 'zod'
import { readResponse } from '@/lib/api/session'

const compareSchema = z.object({
  data: z.object({
    query: z.string(),
    limit: z.number().int().positive(),
    filters: z.object({
      opd_id: z.number().int().positive().nullable(),
      year: z.number().int().nullable(),
      status: z.number().int().nullable(),
    }),
    methods: z.array(
      z.object({
        name: z.string(),
        label: z.string(),
        items: z.array(
          z.object({
            id: z.number().int().positive(),
            summary_raw: z.string().nullable(),
            score: z.number(),
          }),
        ),
      }),
    ),
    score_note: z.string(),
  }),
})

export type CompareResults = z.infer<typeof compareSchema>['data']

export async function getComparison(params: string): Promise<CompareResults> {
  const response = await fetch(`/api/v1/search/compare?${params}`, {
    credentials: 'same-origin',
    cache: 'no-store',
  })
  return compareSchema.parse(await readResponse(response)).data
}
