import { redirect } from "next/navigation";

// Root redirects to dashboard (middleware will handle auth → login)
export default function RootPage() {
  redirect("/dashboard");
}
