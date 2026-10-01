import { StartupSync } from "@/components/StartupSync";
import { BottomBar, Sidebar } from "@/components/TabNav";
import { SetupNotice } from "@/components/SetupNotice";
import { isSupabaseConfigured } from "@/lib/supabase/config";

export default function AppLayout({ children }: LayoutProps<"/">) {
  if (!isSupabaseConfigured) return <SetupNotice />;

  // Am PC füllt jede Seite genau den Bildschirm (kein Scrollen der ganzen Seite),
  // am Handy wird normal gescrollt.
  return (
    <div className="flex min-h-dvh md:h-dvh md:overflow-hidden">
      <StartupSync />
      <Sidebar />
      <main className="flex min-w-0 flex-1 flex-col px-4 pt-5 pb-24 md:px-8 md:py-6">
        <div className="mx-auto flex w-full max-w-[90rem] flex-1 flex-col md:min-h-0">
          {children}
        </div>
      </main>
      <BottomBar />
    </div>
  );
}
