import { Placeholder } from "@/components/Placeholder";
import { TABS } from "@/components/tabs";

export default function GymPage() {
  return <Placeholder tab={TABS.find((t) => t.href === "/gym")!} phase="Phase 2" />;
}
