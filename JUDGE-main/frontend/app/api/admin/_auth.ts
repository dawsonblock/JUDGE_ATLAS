export function buildAdminAuthHeaders(req: Request): {
  headers: HeadersInit;
  configured: boolean;
} {
  const authHeader = req.headers.get("authorization");
  const hasBearer = Boolean(authHeader?.startsWith("Bearer "));
  if (hasBearer && authHeader) {
    return {
      headers: { authorization: authHeader },
      configured: true,
    };
  }

  const legacyEnabled =
    (process.env.JTA_ENABLE_LEGACY_ADMIN_TOKEN || "").toLowerCase() === "true";
  const token = process.env.JTA_ADMIN_TOKEN;
  if (legacyEnabled && token) {
    return {
      headers: { "x-jta-admin-token": token },
      configured: true,
    };
  }

  return { headers: {}, configured: false };
}
