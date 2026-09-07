export default function TabBtn({ active, onClick, label }) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
        active 
          ? 'bg-[#e3dacc]/70 text-[#141413] font-semibold' 
          : 'text-[#87867f] hover:text-[#141413] hover:bg-[#e3dacc]/30'
      }`}
    >
      <span>{label}</span>
    </button>
  )
}
