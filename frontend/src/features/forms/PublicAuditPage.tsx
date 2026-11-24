import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, ArrowRight, CheckCircle2, Lock, Send } from 'lucide-react'
import { useParams } from 'react-router'
import { ErrorStateCard } from '@/components/shared/ErrorStateCard'
import { LoadingState } from '@/components/shared/LoadingState'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { AuditFieldCard, auditFieldLabels } from '@/features/audit/AuditFieldCard'
import { fields } from '@/lib/api/extractionAudit'
import {
  fetchPublicAudit,
  type PublicAuditData,
  savePublicAuditField,
  submitPublicAudit,
} from '@/lib/api/publicTasks'
import { ApiError } from '@/lib/api/session'
import { formatDateTimeId } from '@/lib/format'

export function PublicAuditPage() {
  const { token = '' } = useParams()
  const [index, setIndex] = useState(0)
  const [confirmSubmit, setConfirmSubmit] = useState(false)
  const queryClient = useQueryClient()

  const queryKey = ['public-audit', token, index] as const
  const auditQuery = useQuery({
    queryKey,
    queryFn: () => fetchPublicAudit(token, index),
    enabled: Boolean(token),
    retry: false,
    refetchOnWindowFocus: false,
  })

  const submitMutation = useMutation({
    mutationFn: () => submitPublicAudit(token),
    onSuccess: (res) => {
      const current = auditQuery.data
      if (current) {
        queryClient.setQueryData<PublicAuditData>(queryKey, {
          ...current,
          link: { ...current.link, submitted_at: res.submitted_at },
        })
      }
      void queryClient.invalidateQueries({ queryKey: ['public-audit', token] })
    },
  })

  const data = auditQuery.data
  const state = data?.audit
  const linkInfo = data?.link
  const submittedAt = linkInfo?.submitted_at ?? null

  return (
    <div className="min-h-svh bg-stone-50 px-4 py-6 sm:py-10">
      <main className="mx-auto max-w-4xl space-y-5">
        <header className="space-y-1">
          <p className="text-xs font-medium tracking-wide text-primary uppercase">
            SIMANIS · Audit Ekstraksi Tanpa Login
          </p>
          <h1 className="text-xl font-semibold tracking-tight sm:text-2xl">
            {linkInfo ? linkInfo.label || 'Audit Ekstraksi 5 Field' : 'Audit Ekstraksi Arsip'}
          </h1>
          <p className="text-sm text-muted-foreground">
            Periksa kesesuaian 5 field hasil ekstraksi terhadap teks ringkasan asli arsip.
          </p>
        </header>

        {auditQuery.isPending && (
          <LoadingState label="Membuka tautan audit" rows={2} rowClassName="h-36 w-full" />
        )}

        {auditQuery.isError &&
          (auditQuery.error instanceof ApiError &&
          (auditQuery.error.status === 403 ||
            auditQuery.error.status === 404 ||
            auditQuery.error.status === 410) ? (
            <Alert variant="destructive">
              <AlertTitle>Tautan tidak dapat diakses</AlertTitle>
              <AlertDescription>{auditQuery.error.message}</AlertDescription>
            </Alert>
          ) : (
            <ErrorStateCard
              title={
                auditQuery.error instanceof ApiError
                  ? auditQuery.error.message
                  : 'Tautan audit tidak dapat dibuka.'
              }
              onRetry={() => void auditQuery.refetch()}
            />
          ))}

        {data && linkInfo && state && (
          <>
            <Card size="sm">
              <CardContent className="flex flex-wrap items-center justify-between gap-2 text-xs">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="outline">Penilai: {linkInfo.target_username}</Badge>
                  <Badge variant="secondary">
                    {state.completed_cells}/{state.total_cells} sel dinilai
                  </Badge>
                </div>
                {linkInfo.lock_single_device && (
                  <span className="flex items-center gap-1 text-muted-foreground">
                    <Lock aria-hidden="true" className="size-3.5" /> Terkunci pada perangkat ini
                  </span>
                )}
              </CardContent>
            </Card>

            {submittedAt ? (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base text-primary">
                    <CheckCircle2 aria-hidden="true" className="size-5" />
                    Audit ekstraksi telah diserahkan
                  </CardTitle>
                  <CardDescription>
                    Diserahkan pada {formatDateTimeId(submittedAt)} · {state.completed_samples} dari{' '}
                    {state.total_samples} sampel lengkap dinilai.
                  </CardDescription>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground">
                  Tautan ini otomatis terkunci setelah penyerahan final. Anda dapat menutup halaman
                  ini.
                </CardContent>
              </Card>
            ) : (
              <>
                <Card>
                  <CardHeader>
                    <CardTitle className="flex flex-wrap items-center justify-between gap-2">
                      <h2 className="text-base">
                        Sampel {state.index + 1} dari {state.total_samples}
                      </h2>
                      <Badge variant={state.final ? 'outline' : 'secondary'}>
                        {state.completed_samples}/{state.total_samples} sampel lengkap
                      </Badge>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4 text-sm">
                    <progress
                      className="h-2 w-full accent-primary"
                      value={state.completed_cells}
                      max={state.total_cells}
                      aria-label="Progres audit"
                    />
                    <div className="flex flex-wrap items-center gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={index === 0}
                        onClick={() => setIndex(index - 1)}
                      >
                        <ArrowLeft aria-hidden="true" /> Sebelumnya
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={index + 1 >= state.total_samples}
                        onClick={() => setIndex(index + 1)}
                      >
                        Berikutnya <ArrowRight aria-hidden="true" />
                      </Button>
                      <Label htmlFor="public-audit-jump" className="ml-auto">
                        Ke sampel
                      </Label>
                      <Input
                        id="public-audit-jump"
                        className="w-20"
                        type="number"
                        min={1}
                        max={state.total_samples}
                        defaultValue={state.index + 1}
                        key={state.index}
                        onKeyDown={(event) => {
                          if (event.key === 'Enter') {
                            const value = Number(event.currentTarget.value)
                            if (
                              Number.isInteger(value) &&
                              value >= 1 &&
                              value <= state.total_samples
                            ) {
                              setIndex(value - 1)
                            }
                          }
                        }}
                      />
                    </div>
                    <p>
                      ID arsip: {state.sample.archive_id} · Status: {state.sample.archive_status}
                    </p>
                    <div className="rounded-md border bg-muted/30 p-4">
                      <p className="font-medium">Ringkasan mentah</p>
                      <p className="mt-2 whitespace-pre-wrap break-words">
                        {state.sample.summary_raw}
                      </p>
                    </div>
                  </CardContent>
                </Card>

                <div className="grid gap-4 md:grid-cols-2">
                  {fields.map((field) => (
                    <AuditFieldCard
                      key={`${state.sample.archive_id}-${field}-${state.judgments[field].verdict}-${state.judgments[field].note}`}
                      field={field}
                      value={state.sample[`extracted_${field}`]}
                      archiveId={state.sample.archive_id}
                      fingerprint={state.fingerprint}
                      savedVerdict={state.judgments[field].verdict}
                      savedNote={state.judgments[field].note}
                      csrfToken=""
                      saveFn={(verdict, note) =>
                        savePublicAuditField(
                          token,
                          state.sample.archive_id,
                          field,
                          verdict,
                          note,
                          state.fingerprint,
                        )
                      }
                      onSaved={() =>
                        queryClient.invalidateQueries({ queryKey: ['public-audit', token] })
                      }
                    />
                  ))}
                </div>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Penyerahan final audit</CardTitle>
                    <CardDescription>
                      Lengkapi seluruh {state.total_cells} sel penilaian (
                      {fields.map((f) => auditFieldLabels[f]).join(', ')}) sebelum menyerahkan hasil
                      final.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3 text-sm">
                    {state.final ? (
                      <>
                        <div className="flex items-start gap-2.5">
                          <Checkbox
                            id="audit-confirm-submit"
                            checked={confirmSubmit}
                            onCheckedChange={(value) => setConfirmSubmit(value === true)}
                            className="mt-0.5"
                          />
                          <Label htmlFor="audit-confirm-submit" className="font-normal leading-5">
                            Saya sudah memeriksa seluruh sampel. Penyerahan final mengunci tautan
                            audit ini.
                          </Label>
                        </div>
                        <Button
                          className="min-h-11"
                          disabled={!confirmSubmit || submitMutation.isPending}
                          onClick={() => submitMutation.mutate()}
                        >
                          <Send aria-hidden="true" />{' '}
                          {submitMutation.isPending ? 'Menyerahkan…' : 'Serahkan audit final'}
                        </Button>
                        {submitMutation.error && (
                          <Alert variant="destructive">
                            <AlertDescription>
                              {submitMutation.error instanceof ApiError
                                ? submitMutation.error.message
                                : 'Audit gagal diserahkan.'}
                            </AlertDescription>
                          </Alert>
                        )}
                      </>
                    ) : (
                      <p className="text-muted-foreground">
                        Tersisa {state.total_cells - state.completed_cells} sel yang belum dinilai.
                      </p>
                    )}
                  </CardContent>
                </Card>
              </>
            )}
          </>
        )}
      </main>
    </div>
  )
}
