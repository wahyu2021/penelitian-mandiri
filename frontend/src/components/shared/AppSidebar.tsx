import {
  Archive,
  BookOpen,
  ClipboardCheck,
  ClipboardList,
  Columns2,
  DatabaseBackup,
  LayoutDashboard,
  ListChecks,
  LogOut,
  Scale,
  Search,
  UserRoundCheck,
  UserRound,
  Users,
  type LucideIcon,
} from 'lucide-react'
import { NavLink } from 'react-router'
import { Button } from '@/components/ui/button'
import type { Session } from '@/lib/api/session'

type SidebarItem = {
  path: string
  label: string
  icon: LucideIcon
  adminOnly?: boolean
}

type SidebarGroup = {
  label: string
  items: SidebarItem[]
}

const operationalGroups: SidebarGroup[] = [
  {
    label: 'Arsip',
    items: [
      { path: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
      { path: 'search', label: 'Pencarian', icon: Search },
    ],
  },
  {
    label: 'Pengelolaan data',
    items: [{ path: 'imports', label: 'Impor', icon: DatabaseBackup, adminOnly: true }],
  },
  {
    label: 'Administrasi',
    items: [{ path: 'users', label: 'Akun & Log', icon: Users, adminOnly: true }],
  },
]

const researchGroups: SidebarGroup[] = [
  {
    label: 'Evaluasi',
    items: [
      { path: 'compare', label: 'Perbandingan', icon: Columns2, adminOnly: true },
      { path: 'testsets', label: 'Set uji', icon: ListChecks, adminOnly: true },
      { path: 'relevance', label: 'Penilaian relevansi', icon: ClipboardList },
      { path: 'relevance-admin', label: 'Kelola penilaian', icon: UserRoundCheck, adminOnly: true },
      { path: 'agreement', label: 'Kesepakatan', icon: Scale, adminOnly: true },
      { path: 'extraction-audit', label: 'Audit ekstraksi', icon: ClipboardCheck },
    ],
  },
  {
    label: 'Validasi data',
    items: [{ path: 'spm-types', label: 'Kamus SPM', icon: BookOpen, adminOnly: true }],
  },
]

export function AppBrand({ research = false }: { research?: boolean }) {
  return (
    <div className="flex min-w-0 items-center gap-3">
      <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-primary text-primary-foreground">
        <Archive aria-hidden="true" className="size-4" />
      </span>
      <p className="text-sm leading-snug font-semibold">
        {research ? 'Ruang Penelitian' : 'Sistem Pencarian Arsip'}
      </p>
    </div>
  )
}

export function AppSidebar({
  user,
  research = false,
  onNavigate,
  onLogout,
  loggingOut,
  logoutFailed,
}: {
  user: Session['user']
  research?: boolean
  onNavigate?: () => void
  onLogout: () => void
  loggingOut: boolean
  logoutFailed: boolean
}) {
  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto overscroll-contain">
      <nav aria-label="Navigasi utama" className="flex-1 space-y-5 px-3 py-5">
        {(research ? researchGroups : operationalGroups).map(({ label, items }) => {
          const visible = items.filter((item) => !item.adminOnly || user?.role === 'admin')
          if (!visible.length) return null
          return (
            <section key={label} aria-label={label}>
              <h2 className="px-3 pb-1.5 text-xs font-medium text-muted-foreground">{label}</h2>
              <ul className="space-y-0.5">
                {visible.map(({ path, label, icon: Icon }) => (
                  <li key={path}>
                    <NavLink
                      to={`${research ? '/app/research' : '/app'}/${path}`}
                      onClick={onNavigate}
                      className={({ isActive }) =>
                        `flex min-h-11 items-center gap-3 rounded-md px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                          isActive
                            ? 'bg-primary/10 font-semibold text-primary'
                            : 'text-sidebar-foreground hover:bg-sidebar-accent'
                        }`
                      }
                    >
                      <Icon aria-hidden="true" className="size-4 shrink-0" />
                      {label}
                    </NavLink>
                  </li>
                ))}
              </ul>
            </section>
          )
        })}
        {research && (
          <NavLink
            to="/app/search"
            onClick={onNavigate}
            className="flex min-h-11 items-center gap-3 rounded-md px-3 text-sm text-primary focus-visible:ring-2 focus-visible:ring-ring"
          >
            <Search aria-hidden="true" className="size-4" /> Buka pencarian arsip
          </NavLink>
        )}
      </nav>
      <section aria-label="Akun" className="border-t border-sidebar-border px-4 py-4">
        <h2 className="text-xs font-medium text-muted-foreground">Akun</h2>
        <div className="mt-2 flex items-center gap-2.5">
          <span className="grid size-8 shrink-0 place-items-center rounded-full bg-sidebar-accent">
            <UserRound aria-hidden="true" className="size-4" />
          </span>
          <p className="min-w-0 text-sm break-words">
            {user?.username} · {user?.role === 'admin' ? 'Admin' : 'Petugas'}
          </p>
        </div>
        <Button
          variant="ghost"
          className="mt-2 min-h-11 w-full justify-start"
          disabled={loggingOut}
          onClick={onLogout}
        >
          <LogOut aria-hidden="true" /> {loggingOut ? 'Keluar…' : 'Keluar'}
        </Button>
        {logoutFailed && (
          <p role="alert" className="mt-1 text-sm text-destructive">
            Gagal keluar. Coba lagi.
          </p>
        )}
      </section>
    </div>
  )
}
