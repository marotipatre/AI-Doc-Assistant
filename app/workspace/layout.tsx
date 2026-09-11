import { Workbench } from "@/components/workbench/workbench";
export default function WorkspaceLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <Workbench>{children}</Workbench>;
}
