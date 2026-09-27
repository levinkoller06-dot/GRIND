import { Placeholder } from "@/components/Placeholder";
import { TABS } from "@/components/tabs";

export default function KalenderPage() {
  return <Placeholder tab={TABS.find((t) => t.href === "/kalender")!} phase="Phase 1" />;
}
