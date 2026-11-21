import { z } from 'zod'
import { readResponse } from '@/lib/api/session'

const nullableText = z.string().nullable()

const archiveSchema = z.object({
  data: z.object({
    id: z.number().int().positive(),
    status: z.number().int(),
    year: z.number().int().nullable(),
    opd_name: nullableText,
    classification_label: nullableText,
    file_number: nullableText,
    index_label: nullableText,
    summary_raw: nullableText,
    has_document: z.boolean(),
    location: z.object({
      block: nullableText,
      rack: nullableText,
      row: nullableText,
      box_number: nullableText,
    }),
    extraction: z.object({
      spm_number: nullableText,
      sp2d_number: nullableText,
      document_date: nullableText,
      amount_rp: z.number().nullable(),
      party_name: nullableText,
      spm_type: z
        .object({ code: z.string(), label: nullableText, confidence: nullableText })
        .nullable(),
    }),
  }),
})

export type ArchiveDetail = z.infer<typeof archiveSchema>['data']

export async function getArchiveDetail(id: number): Promise<ArchiveDetail> {
  const response = await fetch(`/api/v1/archives/${id}`, {
    credentials: 'same-origin',
    cache: 'no-store',
  })
  return archiveSchema.parse(await readResponse(response)).data
}
