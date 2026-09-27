import { Placeholder } from "@/components/Placeholder";
import { TABS } from "@/components/tabs";

export default function FreizeitPage() {
  return <Placeholder tab={TABS.find((t) => t.href === "/freizeit")!} phase="Phase 6" />;
}
