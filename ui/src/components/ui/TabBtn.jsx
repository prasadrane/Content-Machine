export default function TabBtn({ active, onClick, label }) {
  return (
    <button
      type="button"
      aria-current={active ? 'page' : undefined}
      onClick={onClick}
      className={`cm-chip ${active ? 'cm-chip-active' : ''}`}
    >
      <span>{label}</span>
    </button>
  )
}
