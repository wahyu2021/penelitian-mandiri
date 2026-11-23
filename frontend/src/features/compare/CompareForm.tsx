import { useState, type FormEvent } from 'react'
import { RotateCcw, Search } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { SearchFilters } from '@/lib/api/search'

const ALL_VALUE = '__all__'

export type CompareFormValues = {
  q: string
  opd_id: string
  year: string
  status: string
  limit: string
}

type Props = {
  initial: CompareFormValues
  options?: SearchFilters
  optionsError: boolean
  retryOptions: () => void
  onCompare: (values: CompareFormValues) => void
  onClear: () => void
}

export function CompareForm({
  initial,
  options,
  optionsError,
  retryOptions,
  onCompare,
  onClear,
}: Props) {
  const [form, setForm] = useState(initial)

  function update(key: keyof CompareFormValues, value: string) {
    setForm((current) => ({ ...current, [key]: value }))
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    onCompare(form)
  }

  function clear() {
    setForm({ q: '', opd_id: '', year: '', status: '', limit: '10' })
    onClear()
  }

  return (
    <Card>
      <CardContent>
        <form onSubmit={submit} className="space-y-5">
          <div className="space-y-2">
            <Label htmlFor="compare-query">Kata kunci</Label>
            <Input
              id="compare-query"
              type="search"
              value={form.q}
              onChange={(event) => update('q', event.target.value)}
              maxLength={200}
              placeholder="Contoh: pembangunan jembatan"
            />
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="space-y-2">
              <Label htmlFor="compare-opd">OPD</Label>
              <Select
                value={form.opd_id || ALL_VALUE}
                onValueChange={(value) => update('opd_id', value === ALL_VALUE ? '' : value)}
              >
                <SelectTrigger id="compare-opd" className="w-full">
                  <SelectValue placeholder="Semua OPD" />
                </SelectTrigger>
                <SelectContent position="popper">
                  <SelectItem value={ALL_VALUE}>Semua OPD</SelectItem>
                  {options?.opds.map((opd) => (
                    <SelectItem key={opd.id} value={String(opd.id)}>
                      {opd.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="compare-year">Tahun</Label>
              <Input
                id="compare-year"
                type="number"
                min={1900}
                max={2100}
                value={form.year}
                onChange={(event) => update('year', event.target.value)}
                placeholder="Semua tahun"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="compare-status">Status</Label>
              <Select
                value={form.status || ALL_VALUE}
                onValueChange={(value) => update('status', value === ALL_VALUE ? '' : value)}
              >
                <SelectTrigger id="compare-status" className="w-full">
                  <SelectValue placeholder="Semua status" />
                </SelectTrigger>
                <SelectContent position="popper">
                  <SelectItem value={ALL_VALUE}>Semua status</SelectItem>
                  <SelectItem value="1">Aktif</SelectItem>
                  <SelectItem value="2">Nonaktif</SelectItem>
                  <SelectItem value="3">Lainnya</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="compare-limit">Hasil per metode</Label>
              <Select value={form.limit} onValueChange={(value) => update('limit', value)}>
                <SelectTrigger id="compare-limit" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent position="popper">
                  {[5, 10, 20].map((limit) => (
                    <SelectItem key={limit} value={String(limit)}>
                      {limit}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          {optionsError && (
            <Alert variant="destructive">
              <AlertDescription className="flex flex-wrap items-center gap-2">
                <span>Pilihan OPD belum dapat dimuat.</span>
                <button type="button" className="underline" onClick={retryOptions}>
                  Coba lagi
                </button>
              </AlertDescription>
            </Alert>
          )}
          <div className="flex flex-wrap gap-2">
            <Button type="submit">
              <Search aria-hidden="true" /> Bandingkan
            </Button>
            <Button type="button" variant="outline" onClick={clear}>
              <RotateCcw aria-hidden="true" /> Bersihkan
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}
