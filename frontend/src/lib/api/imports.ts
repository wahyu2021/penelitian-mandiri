import { z } from 'zod'
import { apiGet, apiMutate } from '@/lib/api/client'

const sourceSchema = z.object({ name: z.string(), size_bytes: z.number().int().nonnegative() })
const historySchema = z.object({
  id: z.number().int().positive(),
  source_filename: z.string(),
  source_sha256: z.string(),
  parser_version: z.string(),
  extractor_version: z.string(),
  raw_count: z.number().int().nonnegative(),
  clean_count: z.number().int().nonnegative(),
  issue_count: z.number().int().nonnegative(),
  status: z.string(),
  imported_by: z.string(),
  imported_at: z.string(),
})
const overviewSchema = z.object({
  data: z.object({
    configured: z.boolean(),
    verify_reference_counts: z.boolean(),
    sources: z.array(sourceSchema),
    history: z.array(historySchema),
  }),
})
const previewSchema = z.object({
  data: z.object({
    source: z.string(),
    source_sha256: z.string(),
    size_bytes: z.number().int().nonnegative(),
    counts: z.object({
      archives: z.number().int().nonnegative(),
      opds: z.number().int().nonnegative(),
      classifications: z.number().int().nonnegative(),
    }),
    reference_archive_count: z.number().int().positive(),
    reference_total_matches: z.boolean(),
  }),
})
const importResultSchema = z.object({
  data: z.object({
    batch_id: z.number().int().positive(),
    source_sha256: z.string(),
    raw_count: z.number().int().nonnegative(),
    clean_count: z.number().int().nonnegative(),
    issue_count: z.number().int().nonnegative(),
    reference_counts_match: z.boolean(),
    backup_filename: z.string().nullable(),
  }),
})

export type ImportOverview = z.infer<typeof overviewSchema>['data']
export type ImportPreview = z.infer<typeof previewSchema>['data']
export type ImportResult = z.infer<typeof importResultSchema>['data']

export function getImportOverview(): Promise<ImportOverview> {
  return apiGet('/api/v1/imports', overviewSchema)
}

export function getImportPreview(source: string): Promise<ImportPreview> {
  const params = new URLSearchParams({ source })
  return apiGet(`/api/v1/imports/preview?${params}`, previewSchema)
}

export function runImport(
  source: string,
  sourceSha256: string,
  csrfToken: string,
): Promise<ImportResult> {
  return apiMutate('/api/v1/imports', 'POST', importResultSchema, {
    csrfToken,
    body: { source, source_sha256: sourceSha256 },
  })
}
