import { useState } from 'react'
import { Download, LockKeyhole } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { TestsetQueryTable } from '@/features/testsets/TestsetQueryTable'
import { TestsetUploadForm } from '@/features/testsets/TestsetUploadForm'
import { testsetExportUrl, type TestsetDetail, type TestsetSummary } from '@/lib/api/testsets'
import { formatDateTimeId } from '@/lib/format'

export function TestsetVersionPanel({
  data,
  busy,
  onSave,
  onLock,
}: {
  data: TestsetDetail
  busy: boolean
  onSave: (file: File, draft?: TestsetSummary) => void
  onLock: (draft: TestsetSummary) => void
}) {
  const [confirmed, setConfirmed] = useState(false)

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>
            <h2 className="break-all">
              {data.version} · {data.locked_at ? 'Terkunci' : 'Terbuka'}
            </h2>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <dl className="grid gap-3 sm:grid-cols-3">
            <div>
              <dt className="text-muted-foreground">Kueri</dt>
              <dd>
                {data.n_queries} varian dari {data.n_base_queries} kueri dasar
              </dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Tuning</dt>
              <dd>
                {data.n_tuning} varian dari {data.n_tuning_base_queries} kueri dasar
              </dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Test</dt>
              <dd>
                {data.n_test} varian dari {data.n_test_base_queries} kueri dasar
              </dd>
            </div>
          </dl>
          <p>
            {data.sources.sintetis} sintetis · {data.sources.arsiparis} nyata (arsiparis)
          </p>
          <p className="break-all text-xs text-muted-foreground">
            SHA-256 <code>{data.content_sha256}</code>
          </p>
          {data.locked_at ? (
            <div className="flex flex-wrap items-center gap-3 border-t pt-4">
              <Button asChild variant="outline">
                <a href={testsetExportUrl(data.version)}>
                  <Download aria-hidden="true" /> Unduh JSON
                </a>
              </Button>
              <p className="text-muted-foreground">Dikunci {formatDateTimeId(data.locked_at)}</p>
            </div>
          ) : (
            <>
              <div className="border-t pt-4">
                <TestsetUploadForm draft={data} busy={busy} onSave={onSave} />
              </div>
              <div className="space-y-3 border-t pt-4">
                <div className="flex items-start gap-2.5">
                  <Checkbox
                    id="testset-lock-confirm"
                    checked={confirmed}
                    onCheckedChange={(value) => setConfirmed(value === true)}
                    className="mt-0.5"
                  />
                  <Label htmlFor="testset-lock-confirm" className="font-normal leading-5">
                    Saya sudah memeriksa kueri dan split. Setelah dikunci, perubahan harus memakai
                    versi baru.
                  </Label>
                </div>
                <Button
                  disabled={busy || !confirmed || !data.n_tuning || !data.n_test}
                  onClick={() => onLock(data)}
                >
                  <LockKeyhole aria-hidden="true" /> Kunci versi
                </Button>
              </div>
            </>
          )}
        </CardContent>
      </Card>
      <TestsetQueryTable queries={data.queries} />
    </>
  )
}
