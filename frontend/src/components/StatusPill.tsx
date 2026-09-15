type StatusPillProps = { active: boolean }

export function StatusPill({ active }: StatusPillProps) {
  return <span className={`status-pill ${active ? 'active' : 'inactive'}`}><i />{active ? 'ACTIVE' : 'INACTIVE'}</span>
}
