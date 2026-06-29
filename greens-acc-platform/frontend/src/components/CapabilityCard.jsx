function CapabilityCard({ icon: Icon, title, description }) {
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-4 inline-flex rounded-xl bg-emerald-50 p-3 text-[#00C853]">
        <Icon size={24} />
      </div>
      <h3 className="mb-2 text-lg font-semibold text-slate-900">{title}</h3>
      <p className="text-sm leading-6 text-slate-600">{description}</p>
    </article>
  )
}

export default CapabilityCard
