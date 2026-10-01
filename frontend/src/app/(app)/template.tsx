// Wird bei jedem Seitenwechsel neu eingehängt → die neue Seite blendet weich ein
export default function Template({ children }: { children: React.ReactNode }) {
  return <div className="page-enter flex flex-1 flex-col md:min-h-0">{children}</div>;
}
