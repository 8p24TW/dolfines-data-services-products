import useSWR from "swr";
import { api } from "@/lib/api";
import type { Site } from "@/types/site";

export function useSites() {
  const { data, error, isLoading, mutate } = useSWR<Site[]>(
    ["sites"],
    () => api.sites.list()
  );

  return { sites: data ?? [], error, isLoading, mutate };
}

export function useSite(siteId: string) {
  const { data, error, isLoading, mutate } = useSWR<Site>(
    siteId ? ["site", siteId] : null,
    ([, id]) => api.sites.get(id as string)
  );

  return { site: data, error, isLoading, mutate };
}
