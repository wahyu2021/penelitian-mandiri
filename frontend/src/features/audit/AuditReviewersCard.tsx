import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Download } from 'lucide-react'
import { LoadingState } from '@/components/shared/LoadingState'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { TaskLinksManager } from '@/features/forms/TaskLinksManager'
import { getAuditReviewers, setAuditReviewer } from '@/lib/api/extractionAudit'
import { adminAuditExportUrl } from '@/lib/api/publicTasks'

export function AuditReviewersCard({ csrfToken }: { csrfToken: string }) {
  const queryClient = useQueryClient()
  const reviewers = useQuery({ queryKey: ['audit-reviewers'], queryFn: getAuditReviewers })
  const mutation = useMutation({
    mutationFn: ({ id, assigned }: { id: number; assigned: boolean }) =>
      setAuditReviewer(id, assigned, csrfToken),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['audit-reviewers'] }),
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <h2 className="text-base">Petugas penilai</h2>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <p className="text-muted-foreground">
          Tugaskan petugas sebelum mereka membuka sampel. Setiap akun memiliki penilaian sendiri.
        </p>
        {reviewers.isPending && (
          <LoadingState label="Memuat petugas penilai" rows={1} rowClassName="h-12 w-full" />
        )}
        {reviewers.isError && (
          <Alert variant="destructive">
            <AlertDescription>Daftar petugas belum dapat dimuat.</AlertDescription>
          </Alert>
        )}
        {reviewers.data?.map((person) => (
          <div key={person.id} className="space-y-3 border-t pt-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-wrap items-center gap-2">
                <span>
                  {person.username} {!person.is_active && '(nonaktif)'}
                </span>
                <Badge variant={person.assigned_at ? 'outline' : 'secondary'}>
                  {person.assigned_at ? 'ditugaskan' : 'belum ditugaskan'}
                </Badge>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Button size="sm" variant="outline" asChild>
                  <a href={adminAuditExportUrl(person.id)}>
                    <Download aria-hidden="true" /> Unduh CSV
                  </a>
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={!person.is_active || mutation.isPending}
                  onClick={() => mutation.mutate({ id: person.id, assigned: !person.assigned_at })}
                >
                  {person.assigned_at ? 'Cabut tugas' : 'Tugaskan'}
                </Button>
              </div>
            </div>
            <TaskLinksManager
              taskKind="extraction_audit"
              userId={person.id}
              csrfToken={csrfToken}
              disabled={!person.is_active}
            />
          </div>
        ))}
        {mutation.isError && (
          <Alert variant="destructive">
            <AlertDescription>Penugasan gagal disimpan.</AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  )
}
