import { Placeholder } from "@/components/Placeholder";
import { TABS } from "@/components/tabs";

export default function GeldPage() {
  return <Placeholder tab={TABS.find((t) => t.href === "/geld")!} phase="Phase 6" />;
}
