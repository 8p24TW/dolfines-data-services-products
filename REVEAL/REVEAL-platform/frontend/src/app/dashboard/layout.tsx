import { Header } from "@/components/layout/Header";
import { I18nProvider } from "@/lib/i18n";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <I18nProvider>
      <div className="flex min-h-screen flex-col">
        <Header />
        <main className="flex-1 w-full">{children}</main>
      </div>
    </I18nProvider>
  );
}
