import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { reviewError, useReviewExpiry } from '@/features/relevance/useReviewSession'
import { migrateReview } from '@/lib/api/relevance'

export function RelevanceLegacyImportForm({
  version,
  slot,
  csrf,
  refresh,
}: {
  version: string
  slot: 1 | 2
  csrf: string
  refresh: () => Promise<unknown>
}) {
  const [file, setFile] = useState<File>()
  const inputId = `legacy-${version}-${slot}`
  const mutation = useMutation({
    mutationFn: (selectedFile: File) => migrateReview(version, slot, selectedFile, csrf),
    onSuccess: refresh,
  })
  useReviewExpiry(mutation.error)

  return (
    <form
      className="space-y-2"
      onSubmit={(event) => {
        event.preventDefault()
        if (file) mutation.mutate(file)
      }}
    >
      <Label htmlFor={inputId}>CSV jawaban lama · Penilai {slot}</Label>
      <div className="flex flex-wrap items-end gap-2">
        <Input
          id={inputId}
          type="file"
          accept=".csv,text/csv"
          className="w-auto max-w-full"
          onChange={(event) => {
            mutation.reset()
            setFile(event.target.files?.[0])
          }}
        />
        <Button
          type="submit"
          variant="outline"
          className="min-h-11"
          disabled={!file || mutation.isPending}
        >
          Impor jawaban
        </Button>
      </div>
      {mutation.isSuccess && (
        <Alert role="status">
          <AlertDescription>
            {mutation.data.inserted} dimigrasikan · {mutation.data.preserved} isian web
            dipertahankan · {mutation.data.outside_rows} baris di luar sampel.
          </AlertDescription>
        </Alert>
      )}
      {mutation.error && (
        <Alert variant="destructive">
          <AlertDescription>
            {reviewError(mutation.error, 'Jawaban lama gagal diimpor.')}
          </AlertDescription>
        </Alert>
      )}
    </form>
  )
}
