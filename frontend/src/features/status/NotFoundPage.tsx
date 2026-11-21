import { Link } from 'react-router'
import { Button } from '@/components/ui/button'

export function NotFoundPage() {
  return (
    <main className="flex min-h-svh items-center justify-center bg-stone-50 px-4">
      <section className="w-full max-w-md rounded-2xl border border-border bg-card p-8">
        <p className="text-sm font-semibold text-muted-foreground">404</p>
        <h1 className="mt-2 text-2xl font-semibold">Halaman tidak ditemukan</h1>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          Alamat yang dibuka tidak tersedia di aplikasi ini.
        </p>
        <Button asChild className="mt-6">
          <Link to="/">Kembali ke awal</Link>
        </Button>
      </section>
    </main>
  )
}
