import { Placeholder } from "@/components/Placeholder";
import { TABS } from "@/components/tabs";

export default function NotenPage() {
  return <Placeholder tab={TABS.find((t) => t.href === "/noten")!} phase="Phase 1" />;
}
