import { describe, expect, it } from "vitest";

import { publicMapMarkersResponseSchema } from "@/lib/schemas";

describe("publicMapMarkersResponseSchema", () => {
  it("accepts a valid map marker payload", () => {
    const payload = {
      items: [
        { entity_id: "event-1", lat: 52.1, lon: -106.7, label: "Court A" },
        { entity_id: "event-2", lat: 51.0, lon: -114.1 },
      ],
    };
    expect(publicMapMarkersResponseSchema.safeParse(payload).success).toBe(true);
  });

  it("rejects map marker payloads without coordinates", () => {
    const payload = {
      items: [{ entity_id: "event-1", lat: 52.1 }],
    };
    expect(publicMapMarkersResponseSchema.safeParse(payload).success).toBe(false);
  });
});
