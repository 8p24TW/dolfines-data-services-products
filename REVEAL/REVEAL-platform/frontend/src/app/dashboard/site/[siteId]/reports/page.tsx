import { redirect } from "next/navigation";

export default function ReportSelectPage({ params }: { params: { siteId: string } }) {
  redirect(`/dashboard/site/${params.siteId}/reports/generate?type=comprehensive`);
}
