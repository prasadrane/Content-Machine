export default function TabBtn({ active, onClick, label }) {
  return (
    <button
      type="button"
      aria-current={active ? 'page' : undefined}
      onClick={onClick}
      className={`min-h-10 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
        active 
          ? 'bg-[#e3dacc]/70 text-[#141413] font-semibold' 
          : 'text-[#87867f] hover:text-[#141413] hover:bg-[#e3dacc]/30'
      }`}
    >
      <span>{label}</span>
    </button>
  )
}
