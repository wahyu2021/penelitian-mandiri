import { useState, type FormEvent } from 'react'
import { Search } from 'lucide-react'
import { useNavigate } from 'react-router'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

export function QuickSearchCard() {
  const navigate = useNavigate()
  const [quickQuery, setQuickQuery] = useState('')

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmed = quickQuery.trim()
    navigate(trimmed ? `/app/search?q=${encodeURIComponent(trimmed)}` : '/app/search')
  }

  return (
    <Card>
      <CardContent>
        <form onSubmit={handleSubmit} className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="min-w-0 flex-1 space-y-2">
            <Label htmlFor="dashboard-quick-search">Pencarian cepat arsip</Label>
            <Input
              id="dashboard-quick-search"
              type="search"
              value={quickQuery}
              onChange={(event) => setQuickQuery(event.target.value)}
              maxLength={200}
              placeholder="Cari nomor SPM, pekerjaan, atau nama pihak…"
            />
          </div>
          <Button type="submit" className="shrink-0">
            <Search aria-hidden="true" /> Cari arsip
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
