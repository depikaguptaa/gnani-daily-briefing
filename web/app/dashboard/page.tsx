import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import Dashboard from "@/components/Dashboard";

type DashboardPageProps = {
  searchParams: Promise<{ episode?: string | string[] }>;
};

export default async function DashboardPage({ searchParams }: DashboardPageProps) {
  const supabase = await createClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) {
    const params = await searchParams;
    const episode = Array.isArray(params.episode) ? params.episode[0] : params.episode;
    const next = episode ? `/dashboard?episode=${encodeURIComponent(episode)}` : "/dashboard";
    redirect(`/sign-in?next=${encodeURIComponent(next)}`);
  }
  return <Dashboard email={data.user.email ?? ""} />;
}
