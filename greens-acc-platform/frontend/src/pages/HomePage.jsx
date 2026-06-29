import {
  ArrowRight,
  BookOpenCheck,
  Building2,
  FileSpreadsheet,
  ShieldCheck,
  WalletCards,
} from 'lucide-react'
import CapabilityCard from '../components/CapabilityCard'
import useSupabase from '../hooks/useSupabase'

const capabilities = [
  {
    icon: ShieldCheck,
    title: 'Father Agent Governance',
    description:
      'Establishes compliance, legal, and risk boundaries before any trading workflow progresses.',
  },
  {
    icon: WalletCards,
    title: 'Son Agent Execution',
    description:
      'Handles negotiation, pricing logistics, and execution-ready deal packaging for operators.',
  },
  {
    icon: FileSpreadsheet,
    title: 'Ledger Synchronization',
    description:
      'Keeps accounting events ready for Supabase-backed reconciliation and audit visibility.',
  },
]

function HomePage() {
  const { isConfigured } = useSupabase()

  return (
    <main className="min-h-screen bg-white">
      <section className="border-b border-slate-200 bg-slate-50">
        <div className="mx-auto flex max-w-6xl flex-col gap-12 px-6 py-20 lg:flex-row lg:items-center lg:justify-between">
          <div className="max-w-3xl">
            <span className="inline-flex rounded-full border border-emerald-200 bg-emerald-50 px-4 py-2 text-sm font-medium text-emerald-700">
              Greens ACC Multi-Agent Corporate Trading Framework
            </span>
            <h1 className="mt-6 text-5xl font-semibold tracking-tight text-slate-950">
              International trading and accounting control in one green command center.
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-600">
              A clean corporate frontend prepared for operations teams, with a FastAPI backend and
              Supabase-ready ledger workflows.
            </p>
            <div className="mt-8 flex flex-wrap gap-4">
              <a className="btn-primary inline-flex items-center gap-2" href="#capabilities">
                Explore capabilities
                <ArrowRight size={18} />
              </a>
              <a className="btn-secondary inline-flex items-center gap-2" href="#deployment">
                Deployment readiness
              </a>
            </div>
          </div>
          <div className="grid gap-4 rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
            <div className="flex items-center gap-3 text-slate-900">
              <Building2 className="text-[#00C853]" />
              <span className="font-semibold">Corporate operations workspace</span>
            </div>
            <div className="flex items-center gap-3 text-slate-900">
              <BookOpenCheck className="text-[#00C853]" />
              <span className="font-semibold">Policy-first negotiation flows</span>
            </div>
            <div className="rounded-2xl bg-slate-950 p-5 text-white">
              <p className="text-sm uppercase tracking-[0.2em] text-emerald-300">Supabase</p>
              <p className="mt-3 text-2xl font-semibold">
                {isConfigured ? 'Configured for live services' : 'Awaiting environment configuration'}
              </p>
            </div>
          </div>
        </div>
      </section>

      <section id="capabilities" className="mx-auto max-w-6xl px-6 py-20">
        <div className="max-w-2xl">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-[#00C853]">
            Architecture highlights
          </p>
          <h2 className="mt-3 text-3xl font-semibold text-slate-950">Purpose-built for Greens ACC</h2>
        </div>
        <div className="mt-10 grid gap-6 md:grid-cols-3">
          {capabilities.map((capability) => (
            <CapabilityCard key={capability.title} {...capability} />
          ))}
        </div>
      </section>

      <section id="deployment" className="bg-slate-950 px-6 py-20 text-white">
        <div className="mx-auto grid max-w-6xl gap-8 lg:grid-cols-2">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-emerald-300">
              Deployment readiness
            </p>
            <h2 className="mt-3 text-3xl font-semibold">Frontend, backend, and database layers separated.</h2>
          </div>
          <div className="space-y-4 text-slate-300">
            <p>Frontend runs on Vite + React with a minimalist white-and-green brand system.</p>
            <p>Backend exposes FastAPI health and platform overview endpoints for Render or Railway.</p>
            <p>Supabase migrations provide a starting ledger schema for deals and accounting events.</p>
          </div>
        </div>
      </section>
    </main>
  )
}

export default HomePage
