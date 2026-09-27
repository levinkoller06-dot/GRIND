import { Placeholder } from "@/components/Placeholder";
import { TABS } from "@/components/tabs";

export default function MailsPage() {
  return <Placeholder tab={TABS.find((t) => t.href === "/mails")!} phase="Phase 4" />;
}
