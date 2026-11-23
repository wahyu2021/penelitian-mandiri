import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { FileUp } from 'lucide-react'
import { EmptyState } from '@/components/shared/EmptyState'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { reviewError, useReviewExpiry } from '@/features/relevance/useReviewSession'
import { createReview, type RelevanceAdmin } from '@/lib/api/relevance'

const EMPTY_VALUE = '__none__'

export function RelevanceSetupCard({
  data,
  csrf,
  refresh,
}: {
  data: RelevanceAdmin
  csrf: string
  refresh: () => Promise<unknown>
}) {
  const [selection, setSelection] = useState('')
  const version = data.available_versions.includes(selection) ? selection : ''
  const [first, setFirst] = useState('')
  const [second, setSecond] = useState('')
  const [file, setFile] = useState<File>()
  const mutation = useMutation({
    mutationFn: (selectedFile: File) => createReview(version, first, second, selectedFile, csrf),
    onSuccess: () => {
      setFile(undefined)
      return refresh()
    },
  })
  useReviewExpiry(mutation.error)

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <h2>Siapkan penugasan</h2>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        {data.available_versions.length === 0 ? (
          <EmptyState message="Belum ada versi terkunci yang siap ditugaskan." />
        ) : (
          <form
            className="space-y-4"
            onSubmit={(event) => {
              event.preventDefault()
              if (file && version && first && second && first !== second) mutation.mutate(file)
            }}
          >
            <p>
              Pilih set uji terkunci dan unggah sampel verifikasi CSV. Pastikan akun penilai tepat
              sebelum menyimpan.
            </p>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="review-version">Versi terkunci</Label>
                <Select
                  value={version || EMPTY_VALUE}
                  onValueChange={(value) => setSelection(value === EMPTY_VALUE ? '' : value)}
                >
                  <SelectTrigger id="review-version" className="w-full">
                    <SelectValue placeholder="Pilih versi" />
                  </SelectTrigger>
                  <SelectContent position="popper">
                    <SelectItem value={EMPTY_VALUE}>Pilih versi</SelectItem>
                    {data.available_versions.map((name) => (
                      <SelectItem value={name} key={name}>
                        {name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="review-sample">Sampel verifikasi CSV</Label>
                <Input
                  key={mutation.isSuccess ? mutation.submittedAt : 'sample'}
                  id="review-sample"
                  type="file"
                  accept=".csv,text/csv"
                  onChange={(event) => setFile(event.target.files?.[0])}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="review-first">Penilai pertama</Label>
                <Select
                  value={first || EMPTY_VALUE}
                  onValueChange={(value) => setFirst(value === EMPTY_VALUE ? '' : value)}
                >
                  <SelectTrigger id="review-first" className="w-full">
                    <SelectValue placeholder="Pilih akun" />
                  </SelectTrigger>
                  <SelectContent position="popper">
                    <SelectItem value={EMPTY_VALUE}>Pilih akun</SelectItem>
                    {data.accounts.map((account) => (
                      <SelectItem key={account.id} value={String(account.id)}>
                        {account.username}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="review-second">Penilai kedua (Petugas)</Label>
                <Select
                  value={second || EMPTY_VALUE}
                  onValueChange={(value) => setSecond(value === EMPTY_VALUE ? '' : value)}
                >
                  <SelectTrigger id="review-second" className="w-full">
                    <SelectValue placeholder="Pilih akun" />
                  </SelectTrigger>
                  <SelectContent position="popper">
                    <SelectItem value={EMPTY_VALUE}>Pilih akun</SelectItem>
                    {data.accounts
                      .filter((account) => account.role === 'petugas')
                      .map((account) => (
                        <SelectItem
                          key={account.id}
                          value={String(account.id)}
                          disabled={first === String(account.id)}
                        >
                          {account.username}
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <Button
              type="submit"
              className="min-h-11"
              disabled={
                !version || !file || !first || !second || first === second || mutation.isPending
              }
            >
              <FileUp aria-hidden="true" /> {mutation.isPending ? 'Menyiapkan…' : 'Buat penugasan'}
            </Button>
          </form>
        )}
        {mutation.isSuccess && (
          <Alert role="status">
            <AlertDescription>
              Penugasan dibuat. {mutation.data.pairs} pasangan unik dari {mutation.data.sample_rows}{' '}
              baris.
            </AlertDescription>
          </Alert>
        )}
        {mutation.error && (
          <Alert variant="destructive">
            <AlertDescription>
              {reviewError(mutation.error, 'Penugasan gagal dibuat.')}
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  )
}
