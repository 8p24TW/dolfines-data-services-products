import { ResetPasswordForm } from "./ResetPasswordForm";

export default function ResetPasswordPage({
  searchParams,
}: {
  searchParams?: { token?: string };
}) {
  return <ResetPasswordForm token={searchParams?.token ?? ""} />;
}
