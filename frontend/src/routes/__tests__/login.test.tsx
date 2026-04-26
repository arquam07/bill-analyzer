import { describe, expect, it } from "vitest";

describe("route modules", () => {
  it("each route exports a Route", async () => {
    const modules = await Promise.all([
      import("../__root"),
      import("../index"),
      import("../login"),
      import("../register"),
      import("../upload"),
      import("../bills.$billId"),
    ]);
    for (const m of modules) {
      expect(m).toHaveProperty("Route");
    }
  });
});
