export default function Icon({ name, active = false }: { name: string; active?: boolean }) {
  return <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><use href={`/kontur-icons.svg#i-${name}`} />{active && <path d="M2 2h3v3H2Z" fill="currentColor" stroke="none" />}</svg>;
}
