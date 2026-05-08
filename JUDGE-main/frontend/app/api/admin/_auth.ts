export function buildAdminAuthHeaders(req: Request): {
  headers: HeadersInit;
  configured: boolean;
} {
  // 1. JWT cookie — preferred; set by /api/auth/login route handler.
  const cookieHeader = req.headers.get("cookie") ?? "";
  const cookieMatch = cookieHeader.match(/(?:^|;\s*)jta_access_token=([^;]+)/);
  const cookieToken = cookieMatch?.[1];
  if (cookieToken) {
    return {
      headers: { authorization: `Bearer ${cookieToken}` },
      configured: true,
    };
  }

  // 2. Explicit Bearer header (e.g. forwarded by a server component).
  const authHeader = req.headers.get("authorization");
  const hasBearer = Boolean(authHeader?.startsWith("Bearer "));
  if (hasBearer && authHeader) {
    return {
      headers: { authorization: authHeader },
      configured: true,
    };
  }

  return { headers: {}, configured: false };
}
