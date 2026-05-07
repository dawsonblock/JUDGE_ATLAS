import { cookies } from "next/headers";
import { PageHeader } from "@/components/layout/PageHeader";
import { fetchJson, AdminSourceItem } from "@/lib/api";
import { SourceControlCard } from "@/components/SourceControlCard";

function getErrorMessage(err: unknown): string {
  const msg = err instanceof Error ? err.message : String(err);
  if (msg.includes("401") || msg.includes("403")) {
    return "Access denied — check JTA_ADMIN_TOKEN / JWT configuration.";
  }
  if (msg.includes("503")) {
    return "Admin auth not configured — set JTA_ADMIN_TOKEN and JTA_ENABLE_LEGACY_ADMIN_TOKEN in your environment.";
  }
  if (msg.includes("500")) {
    return "Backend error (500) — check backend logs.";
  }
  return `Failed to load sources: ${msg}`;
}

export default async function AdminSourcesPage() {
  let sources: AdminSourceItem[] = [];
  let errorMessage: string | null = null;

  try {
    const cookieStore = cookies();
    const accessToken = cookieStore.get("jta_access_token")?.value ?? "";
    sources = await fetchJson<AdminSourceItem[]>("/api/admin/sources", {
      headers: accessToken ? { authorization: `Bearer ${accessToken}` } : {},
    });
  } catch (err) {
    errorMessage = getErrorMessage(err);
  }

  const activeSources = sources.filter((s) => s.is_active);
  const byAuthority = sources.reduce<Record<string, number>>((acc, s) => {
    acc[s.public_record_authority] = (acc[s.public_record_authority] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      <PageHeader
        title="Source Registry"
        subtitle={`${sources.length} registered · ${activeSources.length} active`}
      />

      {errorMessage && (
        <div className="rounded border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {errorMessage}
        </div>
      )}

      {/* Summary bar */}
      {!errorMessage && (
        <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
          {Object.entries(byAuthority).sort(([, a], [, b]) => b - a).map(([auth, count]) => (
            <span key={auth} className="rounded border px-2 py-0.5">
              {auth.replace(/_/g, " ")}: {count}
            </span>
          ))}
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {sources.map((source) => (
          <SourceControlCard key={source.id} source={source} />
        ))}
      </div>

      {!errorMessage && sources.length === 0 && (
        <p className="text-sm text-muted-foreground">No sources found.</p>
      )}
    </div>
  );
}


