import { NextRequest, NextResponse } from "next/server";
import { buildAdminAuthHeaders } from "../../../_auth";

const backendBase =
  process.env.BACKEND_INTERNAL_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "http://localhost:8000";

/**
 * POST /api/admin/ingestion-runs/[runId]/retry
 *
 * Proxies to the backend POST /api/admin/ingestion-runs/{run_id}/retry
 * with server-side admin auth injection.
 *
 * This route is required because the frontend SourceControlCard.tsx calls
 * this endpoint directly, and admin authentication is forwarded from
 * the httpOnly JWT session cookie.
 */
export async function POST(
  req: NextRequest,
  { params }: { params: { runId: string } },
) {
  const { headers: authHeaders, configured } = buildAdminAuthHeaders(req);
  if (!configured) {
    return NextResponse.json(
      { error: "Admin auth not configured (Bearer JWT required)" },
      { status: 503 },
    );
  }

  const upstream = await fetch(
    `${backendBase}/api/admin/ingestion-runs/${params.runId}/retry`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...authHeaders,
      },
      cache: "no-store",
    },
  );

  const body = await upstream.json().catch(() => ({}));
  return NextResponse.json(body, { status: upstream.status });
}
