import { useState } from 'react'
import { FileUp } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import type { TestsetSummary } from '@/lib/api/testsets'

export function TestsetUploadForm({
  draft,
  busy,
  onSave,
}: {
  draft?: TestsetSummary
  busy: boolean
  onSave: (file: File, draft?: TestsetSummary) => void
}) {
  const [file, setFile] = useState<File>()
  const id = draft ? 'draft-testset-file' : 'new-testset-file'

  return (
    <form
      className="flex flex-wrap items-end gap-3"
      onSubmit={(event) => {
        event.preventDefault()
        if (file) onSave(file, draft)
      }}
    >
      <div className="min-w-0 flex-1 space-y-1.5">
        <Label htmlFor={id}>
          {draft ? 'JSON pengganti untuk versi ini' : 'Berkas JSON set uji baru'}
        </Label>
        <Input
          id={id}
          type="file"
          accept=".json,application/json"
          onChange={(event) => setFile(event.target.files?.[0])}
        />
      </div>
      <Button type="submit" variant={draft ? 'outline' : 'default'} disabled={!file || busy}>
        <FileUp aria-hidden="true" /> {draft ? 'Ganti isi draf' : 'Daftarkan versi'}
      </Button>
    </form>
  )
}
