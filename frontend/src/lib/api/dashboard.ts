import { z } from 'zod'
import { readResponse } from '@/lib/api/session'

const dashboardSchema = z.object({
  data: z.object({
    counts: z.object({
      total: z.number().int().nonnegative(),
      active: z.number().int().nonnegative(),
      inactive: z.number().int().nonnegative(),
      with_file: z.number().int().nonnegative(),
    }),
    recent: z.array(
      z.object({
        id: z.number().int().positive(),
        year: z.number().int().nullable(),
        summary_raw: z.string().nullable(),
        opd_name: z.string().nullable().optional(),
      }),
    ),
    latest_import: z
      .object({
        source_filename: z.string(),
        imported_at: z.string(),
        clean_count: z.number().int().nonnegative(),
      })
      .nullable()
      .optional(),
  }),
})

export type Dashboard = z.infer<typeof dashboardSchema>['data']

export async function getDashboard(): Promise<Dashboard> {
  const response = await fetch('/api/v1/dashboard', {
    credentials: 'same-origin',
    cache: 'no-store',
  })
  return dashboardSchema.parse(await readResponse(response)).data
}
