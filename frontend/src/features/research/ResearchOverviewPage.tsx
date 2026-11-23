import { useQuery } from '@tanstack/react-query'
import {
  ArrowRight,
  BookOpen,
  ClipboardCheck,
  ClipboardList,
  Columns2,
  ListChecks,
  Scale,
  UserRoundCheck,
} from 'lucide-react'
import { Link } from 'react-router'
import { ErrorStateCard } from '@/components/shared/ErrorStateCard'
import { LoadingState } from '@/components/shared/LoadingState'
import { PageHeader } from '@/components/shared/PageHeader'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { AgreementStatusBadge } from '@/features/agreement/AgreementStatusBadge'
import { useSession } from '@/features/auth/useSession'
import { useUnauthorizedRedirect } from '@/hooks/useUnauthorizedRedirect'
import { fetchAgreementSummary } from '@/lib/api/agreement'
import { getSpmTypes } from '@/lib/api/extractionAudit'
import { getTestsets } from '@/lib/api/testsets'
import { formatNumber } from '@/lib/format'

const WORKFLOW_STEPS = [
  {
    step: 'Langkah 1',
    title: 'Set uji terkunci',
    description:
      'Tetapkan versi kueri uji dan pisahkan kueri tuning/test sebelum eksperimen berjalan.',
    to: '/app/research/testsets',
    cta: 'Kelola set uji',
    icon: ListChecks,
  },
  {
    step: 'Langkah 2',
    title: 'Penilaian relevansi dua penilai',
    description:
      'Admin membuat tugas penilaian buta dan memantau progres, lalu setiap penilai menilai pasangan.',
    to: '/app/research/relevance-admin',
    secondaryTo: '/app/research/relevance',
    cta: 'Kelola penugasan',
    secondaryCta: 'Buka form nilai',
    icon: UserRoundCheck,
  },
  {
    step: 'Langkah 3',
    title: 'Kesepakatan & validasi ekstraksi',
    description:
      'Hitung Cohen’s kappa antar penilai, audit 5 field ekstraksi, dan konfirmasi kamus kode SPM.',
    to: '/app/research/agreement',
    secondaryTo: '/app/research/spm-types',
    cta: 'Lihat kesepakatan',
    secondaryCta: 'Kamus SPM',
    icon: Scale,
  },
  {
    step: 'Langkah 4',
    title: 'Demo perbandingan 5 metode',
    description:
      'Bandingkan hasil SQL LIKE, TF-IDF, BM25, Levenshtein, dan Hybrid secara berdampingan untuk satu kueri.',
    to: '/app/research/compare',
    cta: 'Buka perbandingan',
    icon: Columns2,
  },
] as const

export function ResearchOverviewPage() {
  const { data: session } = useSession()
  const isAdmin = session?.user?.role === 'admin'

  const testsets = useQuery({ queryKey: ['testsets'], queryFn: getTestsets, enabled: isAdmin })
  const agreement = useQuery({
    queryKey: ['research-agreement', null, null],
    queryFn: () => fetchAgreementSummary(),
    enabled: isAdmin,
  })
  const spmTypes = useQuery({ queryKey: ['spm-types'], queryFn: getSpmTypes, enabled: isAdmin })

  useUnauthorizedRedirect([testsets.error, agreement.error, spmTypes.error])

  if (!isAdmin) {
    return (
      <main className="space-y-6 py-5 sm:py-6">
        <PageHeader
          eyebrow="Ruang penelitian"
          title="Tugas penilaian peneliti/petugas"
          description="Pilih tugas penilaian yang ditugaskan kepada akun ini."
        />
        <div className="grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <ClipboardList aria-hidden="true" className="size-4 text-primary" />
                Penilaian relevansi
              </CardTitle>
              <CardDescription>
                Nilai kecocokan kebutuhan informasi dengan ringkasan asli arsip secara buta.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild>
                <Link to="/app/research/relevance">
                  Buka penilaian <ArrowRight aria-hidden="true" />
                </Link>
              </Button>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <ClipboardCheck aria-hidden="true" className="size-4 text-primary" />
                Audit ekstraksi
              </CardTitle>
              <CardDescription>
                Periksa ketepatan ekstraksi otomatis untuk SPM, SP2D, tanggal, nominal, dan pihak.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild variant="outline">
                <Link to="/app/research/extraction-audit">
                  Buka audit <ArrowRight aria-hidden="true" />
                </Link>
              </Button>
            </CardContent>
          </Card>
        </div>
      </main>
    )
  }

  const lockedCount = testsets.data?.filter((item) => item.locked_at !== null).length ?? 0
  const latestRelevance = agreement.data?.relevance[0]
  const spmConfirmed =
    spmTypes.data?.filter((item) => item.confidence === 'terkonfirmasi').length ?? 0
  const spmSuspect = spmTypes.data?.filter((item) => item.confidence === 'dugaan').length ?? 0
  const anyError = testsets.isError || agreement.isError || spmTypes.isError
  const isLoading = testsets.isPending || agreement.isPending || spmTypes.isPending

  return (
    <main className="space-y-6 py-5 sm:py-6">
      <PageHeader
        eyebrow="Ruang penelitian"
        title="Ringkasan alur penelitian"
        description="Peta singkat dari penyiapan set uji, penilaian dua penilai, validasi kesepakatan, hingga demo pencarian."
        actions={
          <Button asChild>
            <Link to="/app/research/compare">
              <Columns2 aria-hidden="true" /> Demo perbandingan 5 metode
            </Link>
          </Button>
        }
      />

      {isLoading && (
        <LoadingState label="Memuat status penelitian" rows={1} rowClassName="h-28 w-full" />
      )}

      {anyError && (
        <ErrorStateCard
          title="Sebagian ringkasan penelitian belum dapat dimuat."
          onRetry={() => {
            void testsets.refetch()
            void agreement.refetch()
            void spmTypes.refetch()
          }}
        />
      )}

      {!isLoading && !anyError && (
        <section
          aria-label="Status data penelitian"
          className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"
        >
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Set uji kueri</CardDescription>
              <CardTitle className="text-2xl tabular-nums">
                {formatNumber(testsets.data?.length ?? 0)} versi
              </CardTitle>
            </CardHeader>
            <CardContent className="text-xs text-muted-foreground">
              {formatNumber(lockedCount)} terkunci siap untuk eksperimen
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Kesepakatan relevansi</CardDescription>
              <CardTitle className="text-2xl tabular-nums">
                {formatNumber(agreement.data?.relevance.length ?? 0)} sesi
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              {latestRelevance ? (
                <AgreementStatusBadge status={latestRelevance.status} />
              ) : (
                <span>Belum ada tugas penilaian</span>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Audit ekstraksi 5 field</CardDescription>
              <CardTitle className="text-base">
                {agreement.data?.audit ? (
                  <AgreementStatusBadge status={agreement.data.audit.status} />
                ) : (
                  'Belum ada data'
                )}
              </CardTitle>
            </CardHeader>
            <CardContent className="text-xs text-muted-foreground">
              {agreement.data?.audit.dataset
                ? `${formatNumber(agreement.data.audit.dataset.sample_count)} arsip sampel`
                : 'Belum ada penilaian tersimpan'}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Kamus kode SPM</CardDescription>
              <CardTitle className="flex items-center gap-2 text-2xl tabular-nums">
                <BookOpen aria-hidden="true" className="size-4 text-muted-foreground" />
                {formatNumber(spmTypes.data?.length ?? 0)} kode
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-1.5 text-xs">
              <Badge variant="outline">{formatNumber(spmConfirmed)} terkonfirmasi</Badge>
              <Badge variant="secondary">{formatNumber(spmSuspect)} dugaan</Badge>
            </CardContent>
          </Card>
        </section>
      )}

      <section aria-label="Tahapan penelitian" className="space-y-3">
        <h2 className="text-base font-semibold">Alur kerja di ruang penelitian</h2>
        <div className="grid gap-4 md:grid-cols-2">
          {WORKFLOW_STEPS.map((item) => {
            const Icon = item.icon
            return (
              <Card key={item.title} className="flex flex-col justify-between">
                <CardHeader>
                  <div className="flex items-center justify-between gap-2">
                    <Badge variant="outline">{item.step}</Badge>
                    <Icon aria-hidden="true" className="size-4 text-muted-foreground" />
                  </div>
                  <CardTitle className="pt-1 text-base">{item.title}</CardTitle>
                  <CardDescription>{item.description}</CardDescription>
                </CardHeader>
                <CardContent className="flex flex-wrap gap-2">
                  <Button asChild variant="outline" size="sm">
                    <Link to={item.to}>
                      {item.cta} <ArrowRight aria-hidden="true" />
                    </Link>
                  </Button>
                  {'secondaryTo' in item && item.secondaryTo && (
                    <Button asChild variant="ghost" size="sm">
                      <Link to={item.secondaryTo}>{item.secondaryCta}</Link>
                    </Button>
                  )}
                </CardContent>
              </Card>
            )
          })}
        </div>
      </section>
    </main>
  )
}
