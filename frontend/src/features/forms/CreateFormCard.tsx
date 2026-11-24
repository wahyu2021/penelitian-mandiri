import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Plus, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { createSurveyForm } from '@/lib/api/publicForms'
import { ApiError } from '@/lib/api/session'

type DraftQuestion = {
  id: string
  type: 'scale' | 'choice' | 'text' | 'textarea'
  label: string
  optionsText: string
  required: boolean
}

export function CreateFormCard({
  csrfToken,
  onCreated,
}: {
  csrfToken: string
  onCreated: (formId: number) => void
}) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [questions, setQuestions] = useState<DraftQuestion[]>([
    { id: 'q1', type: 'scale', label: '', optionsText: '', required: true },
  ])
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const susMutation = useMutation({
    mutationFn: () =>
      createSurveyForm(
        {
          title: 'Kuesioner SUS & Umpan Balik Petugas',
          description: 'Evaluasi kegunaan sistem pencarian arsip SIMANIS (skala 1–5).',
          form_kind: 'sus',
        },
        csrfToken,
      ),
    onSuccess: (created) => {
      setErrorMsg(null)
      onCreated(created.id)
    },
    onError: (err) =>
      setErrorMsg(err instanceof ApiError ? err.message : 'Gagal membuat template SUS.'),
  })

  const customMutation = useMutation({
    mutationFn: () =>
      createSurveyForm(
        {
          title,
          description,
          form_kind: 'custom',
          questions: questions.map((q, idx) => ({
            id: `p${idx + 1}`,
            type: q.type,
            label: q.label,
            required: q.required,
            options:
              q.type === 'choice'
                ? q.optionsText
                    .split(',')
                    .map((s) => s.trim())
                    .filter(Boolean)
                : undefined,
          })),
        },
        csrfToken,
      ),
    onSuccess: (created) => {
      setErrorMsg(null)
      setTitle('')
      setDescription('')
      setQuestions([{ id: 'q1', type: 'scale', label: '', optionsText: '', required: true }])
      onCreated(created.id)
    },
    onError: (err) =>
      setErrorMsg(err instanceof ApiError ? err.message : 'Gagal menyimpan formulir.'),
  })

  return (
    <Card>
      <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <CardTitle>Buat formulir baru</CardTitle>
          <CardDescription>
            Gunakan Template SUS 10 butir siap pakai atau susun kuesioner kustom sendiri.
          </CardDescription>
        </div>
        <Button
          type="button"
          variant="outline"
          disabled={susMutation.isPending}
          onClick={() => susMutation.mutate()}
        >
          <Plus aria-hidden="true" />
          {susMutation.isPending ? 'Membuat…' : 'Buat template SUS 10 butir'}
        </Button>
      </CardHeader>

      <CardContent>
        <form
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault()
            setErrorMsg(null)
            customMutation.mutate()
          }}
        >
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="form-custom-title">Judul kuesioner kustom</Label>
              <Input
                id="form-custom-title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Mis. Umpan balik pencarian arsip"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="form-custom-desc">Deskripsi singkat (opsional)</Label>
              <Input
                id="form-custom-desc"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Keterangan singkat untuk responden"
              />
            </div>
          </div>

          <div className="space-y-3">
            {questions.map((q, idx) => (
              <Card key={q.id} size="sm" className="bg-muted/20">
                <CardContent className="space-y-2">
                  <div className="grid gap-2 sm:grid-cols-[1fr_11rem_auto]">
                    <div className="space-y-1">
                      <Label htmlFor={`q-label-${q.id}`}>Pertanyaan #{idx + 1}</Label>
                      <Input
                        id={`q-label-${q.id}`}
                        value={q.label}
                        onChange={(e) =>
                          setQuestions((prev) =>
                            prev.map((item) =>
                              item.id === q.id ? { ...item, label: e.target.value } : item,
                            ),
                          )
                        }
                        placeholder="Tulis pertanyaan"
                      />
                    </div>
                    <div className="space-y-1">
                      <Label htmlFor={`q-type-${q.id}`}>Tipe jawaban</Label>
                      <Select
                        value={q.type}
                        onValueChange={(val) =>
                          setQuestions((prev) =>
                            prev.map((item) =>
                              item.id === q.id
                                ? { ...item, type: val as DraftQuestion['type'] }
                                : item,
                            ),
                          )
                        }
                      >
                        <SelectTrigger
                          id={`q-type-${q.id}`}
                          aria-label={`Tipe pertanyaan ${idx + 1}`}
                        >
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="scale">Skala 1–5</SelectItem>
                          <SelectItem value="choice">Pilihan ganda</SelectItem>
                          <SelectItem value="text">Teks singkat</SelectItem>
                          <SelectItem value="textarea">Catatan panjang</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="flex items-end">
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        aria-label={`Hapus pertanyaan ${idx + 1}`}
                        disabled={questions.length <= 1}
                        onClick={() =>
                          setQuestions((prev) => prev.filter((item) => item.id !== q.id))
                        }
                      >
                        <Trash2 aria-hidden="true" />
                      </Button>
                    </div>
                  </div>
                  {q.type === 'choice' && (
                    <div className="space-y-1">
                      <Label htmlFor={`q-opts-${q.id}`}>Opsi pilihan (pisahkan dengan koma)</Label>
                      <Textarea
                        id={`q-opts-${q.id}`}
                        rows={1}
                        value={q.optionsText}
                        onChange={(e) =>
                          setQuestions((prev) =>
                            prev.map((item) =>
                              item.id === q.id ? { ...item, optionsText: e.target.value } : item,
                            ),
                          )
                        }
                        placeholder="Sangat membantu, Cukup membantu, Perlu perbaikan"
                      />
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() =>
                setQuestions((prev) => [
                  ...prev,
                  {
                    id: `q${prev.length + 1}-${Date.now()}`,
                    type: 'text',
                    label: '',
                    optionsText: '',
                    required: true,
                  },
                ])
              }
            >
              <Plus aria-hidden="true" /> Tambah pertanyaan
            </Button>

            <Button type="submit" disabled={customMutation.isPending}>
              {customMutation.isPending ? 'Menyimpan…' : 'Simpan kuesioner kustom'}
            </Button>
          </div>

          {errorMsg && (
            <p role="alert" className="text-xs text-destructive">
              {errorMsg}
            </p>
          )}
        </form>
      </CardContent>
    </Card>
  )
}
