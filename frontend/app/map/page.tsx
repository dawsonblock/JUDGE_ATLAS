import { redirect } from "next/navigation";

/**
 * Legacy Leaflet map route — redirects to the canonical MapLibre route.
 * This page is kept as a permanent redirect stub so existing bookmarks
 * and external links continue to resolve.
 */
export default function MapPage() {
  redirect("/map-v2");
}
