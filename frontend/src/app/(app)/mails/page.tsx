import { Inbox } from "@/components/Inbox";
import { PageHeader } from "@/components/PageHeader";
import { TABS } from "@/components/tabs";

const tab = TABS.find((t) => t.href === "/mails")!;

export default function MailsPage() {
  return (
    <div className="flex flex-col md:min-h-0 md:flex-1">
      <PageHeader tab={tab} />
      <Inbox />
    </div>
  );
}
