import { BottomBar, Sidebar } from "@/components/TabNav";
import { SetupNotice } from "@/components/SetupNotice";
import { isSupabaseConfigured } from "@/lib/supabase/config";

export default function AppLayout({ children }: LayoutProps<"/">) {
  if (!isSupabaseConfigured) return <SetupNotice />;

  return (
    <div className="flex min-h-dvh">
      <Sidebar />
      <main className="flex-1 px-4 pt-6 pb-24 md:px-10 md:pb-10">
        <div className="mx-auto max-w-3xl">{children}</div>
      </main>
      <BottomBar />
    </div>
  );
}
