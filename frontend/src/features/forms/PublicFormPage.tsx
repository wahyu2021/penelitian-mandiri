import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { CheckCircle2, Lock, ShieldCheck } from 'lucide-react'
import { useParams } from 'react-router'
import { ErrorStateCard } from '@/components/shared/ErrorStateCard'
import { LoadingState } from '@/components/shared/LoadingState'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { fetchPublicForm, submitPublicForm, type PublicSubmitResult } from '@/lib/api/publicForms'
import { ApiError } from '@/lib/api/session'
import { formatDateTimeId } from '@/lib/format'

const SCALE_OPTIONS = [1, 2, 3, 4, 5] as const

export function PublicFormPage() {
  const { token = '' } = useParams()
  const [answers, setAnswers] = useState<Record<string, string | number>>({})
  const [submittedResult, setSubmittedResult] = useState<PublicSubmitResult | null>(null)
  const [formError, setFormError] = useState<string | null>(null)

  const query = useQuery({
    queryKey: ['public-form', token],
    queryFn: () => fetchPublicForm(token),
    enabled: Boolean(token),
    retry: false,
  })

  const mutation = useMutation({
    mutationFn: () => submitPublicForm(token, answers),
    onSuccess: (res) => {
      setFormError(null)
      setSubmittedResult(res)
    },
    onError: (err) => {
      setFormError(err instanceof ApiError ? err.message : 'Jawaban belum dapat dikirim.')
    },
  })

  const data = query.data

  return (
    <div className="min-h-svh bg-stone-50 px-4 py-6 sm:py-10">
      <main className="mx-auto max-w-2xl space-y-5">
        <header className="space-y-1 text-center sm:text-left">
          <p className="text-xs font-medium tracking-wide text-primary uppercase">
            SIMANIS · Pengumpulan Data Tanpa Login
          </p>
          <h1 className="text-xl font-semibold tracking-tight sm:text-2xl">
            {data ? data.form.title : 'Formulir Kuesioner'}
          </h1>
          {data?.form.description && (
            <p className="text-sm text-muted-foreground">{data.form.description}</p>
          )}
        </header>

        {query.isPending && (
          <LoadingState label="Membuka tautan formulir" rows={2} rowClassName="h-32 w-full" />
        )}

        {query.isError &&
          (query.error instanceof ApiError &&
          (query.error.status === 403 ||
            query.error.status === 404 ||
            query.error.status === 410) ? (
            <Alert variant="destructive">
              <AlertTitle>Tautan tidak dapat diakses</AlertTitle>
              <AlertDescription>{query.error.message}</AlertDescription>
            </Alert>
          ) : (
            <ErrorStateCard
              title={
                query.error instanceof ApiError
                  ? query.error.message
                  : 'Tautan formulir tidak dapat dibuka.'
              }
              onRetry={() => void query.refetch()}
            />
          ))}

        {data && (data.already_submitted || submittedResult) && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base text-primary">
                <CheckCircle2 aria-hidden="true" className="size-5" />
                Terima kasih, jawaban Anda sudah tercatat
              </CardTitle>
              <CardDescription>
                Kode peserta: <strong>{data.participant_code}</strong> · Dikirim pada{' '}
                {(submittedResult?.submitted_at ?? data.submitted_at)
                  ? formatDateTimeId(submittedResult?.submitted_at ?? data.submitted_at ?? '')
                  : 'Baru saja'}
              </CardDescription>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Tautan ini telah selesai digunakan dan tidak menerima pengisian ulang. Anda dapat
              menutup halaman ini.
            </CardContent>
          </Card>
        )}

        {data && !data.already_submitted && !submittedResult && (
          <>
            <Card size="sm">
              <CardContent className="flex flex-wrap items-center justify-between gap-2 text-xs">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="outline">Kode peserta: {data.participant_code}</Badge>
                  <Badge variant="secondary">{data.participant_role}</Badge>
                </div>
                {data.lock_single_device && (
                  <span className="flex items-center gap-1 text-muted-foreground">
                    <Lock aria-hidden="true" className="size-3.5" /> Terkunci pada perangkat ini
                  </span>
                )}
              </CardContent>
            </Card>

            {data.form.form_kind === 'sus' && (
              <Alert role="note">
                <ShieldCheck aria-hidden="true" className="size-4" />
                <AlertTitle>Petunjuk pengisian skala 1–5</AlertTitle>
                <AlertDescription>
                  1 = Sangat tidak setuju · 2 = Tidak setuju · 3 = Netral · 4 = Setuju · 5 = Sangat
                  setuju.
                </AlertDescription>
              </Alert>
            )}

            <form
              className="space-y-4"
              onSubmit={(event) => {
                event.preventDefault()
                setFormError(null)
                mutation.mutate()
              }}
            >
              {data.form.questions.map((q, index) => (
                <Card key={q.id}>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm leading-snug font-medium">
                      {index + 1}. {q.label}
                      {q.required && <span className="ml-1 text-destructive">*</span>}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {q.type === 'scale' && (
                      <div
                        role="radiogroup"
                        aria-label={q.label}
                        className="grid grid-cols-5 gap-2"
                      >
                        {SCALE_OPTIONS.map((score) => {
                          const active = answers[q.id] === score
                          return (
                            <Button
                              key={score}
                              type="button"
                              variant={active ? 'default' : 'outline'}
                              className="h-11 text-base font-semibold"
                              aria-pressed={active}
                              onClick={() => setAnswers((prev) => ({ ...prev, [q.id]: score }))}
                            >
                              {score}
                            </Button>
                          )
                        })}
                      </div>
                    )}

                    {q.type === 'choice' && q.options && (
                      <div role="radiogroup" aria-label={q.label} className="grid gap-2">
                        {q.options.map((opt) => {
                          const active = answers[q.id] === opt
                          return (
                            <Button
                              key={opt}
                              type="button"
                              variant={active ? 'default' : 'outline'}
                              className="min-h-10 justify-start text-left whitespace-normal"
                              aria-pressed={active}
                              onClick={() => setAnswers((prev) => ({ ...prev, [q.id]: opt }))}
                            >
                              {opt}
                            </Button>
                          )
                        })}
                      </div>
                    )}

                    {q.type === 'text' && (
                      <div className="space-y-1">
                        <Label htmlFor={`q-${q.id}`} className="sr-only">
                          {q.label}
                        </Label>
                        <Input
                          id={`q-${q.id}`}
                          value={String(answers[q.id] ?? '')}
                          onChange={(e) =>
                            setAnswers((prev) => ({ ...prev, [q.id]: e.target.value }))
                          }
                          placeholder="Tulis jawaban singkat…"
                        />
                      </div>
                    )}

                    {q.type === 'textarea' && (
                      <div className="space-y-1">
                        <Label htmlFor={`q-${q.id}`} className="sr-only">
                          {q.label}
                        </Label>
                        <Textarea
                          id={`q-${q.id}`}
                          rows={3}
                          value={String(answers[q.id] ?? '')}
                          onChange={(e) =>
                            setAnswers((prev) => ({ ...prev, [q.id]: e.target.value }))
                          }
                          placeholder="Tulis catatan bila ada…"
                        />
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}

              {formError && (
                <Alert variant="destructive">
                  <AlertTitle>Pengiriman belum berhasil</AlertTitle>
                  <AlertDescription>{formError}</AlertDescription>
                </Alert>
              )}

              <Button type="submit" size="lg" className="w-full" disabled={mutation.isPending}>
                {mutation.isPending ? 'Mengirim jawaban…' : 'Kirim jawaban'}
              </Button>
            </form>
          </>
        )}
      </main>
    </div>
  )
}
