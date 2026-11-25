// @effect-diagnostics nodeBuiltinImport:off - bootstrap integration exercises the filesystem and fetch.
import * as NodeFS from "node:fs";
import * as NodeOS from "node:os";
import * as NodePath from "node:path";
import { expect, it, vi } from "vite-plus/test";
import { flushTelemetry, observeSummaries, summarize } from "./telemetry.ts";

it("never creates a collector queue or sends an old queued event", async () => {
  const home = NodeFS.mkdtempSync(NodePath.join(NodeOS.tmpdir(), "t3-privacy-"));
  try {
    const stop = observeSummaries(
      home,
      "https://collector.example",
      { T3_TASK_CACHE_TELEMETRY: "on" },
      home,
    );
    expect(NodeFS.existsSync(NodePath.join(home, ".cache"))).toBe(false);
    stop();
    const queue = NodePath.join(home, ".cache/t3-task-cache/telemetry");
    NodeFS.mkdirSync(queue, { recursive: true });
    const event = NodePath.join(queue, "pending.json");
    NodeFS.writeFileSync(event, '{"private":"old event"}');
    using send = vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("must not send"));
    await flushTelemetry(home, { T3_TASK_CACHE_TELEMETRY: "on" });
    expect(send).not.toHaveBeenCalled();
    expect(NodeFS.readFileSync(event, "utf8")).toBe('{"private":"old event"}');
  } finally {
    NodeFS.rmSync(home, { recursive: true });
  }
});

const task = (result: unknown) => ({
  package_name: "@team/server",
  task_name: "typecheck",
  command: "SECRET",
  cwd: "/private",
  result,
});

it("counts only confirmed hits, preserves their tier, and never transmits command text", () => {
  expect(
    summarize({
      tasks: [
        task({ CacheHit: { source: "Remote", saved_duration_ms: 1200 } }),
        task({ CacheHit: { source: "Local", saved_duration_ms: 500 } }),
        task({ RestoreFailed: {} }),
        task({ Spawned: {} }),
        task({ CacheHit: { saved_duration_ms: 999 } }),
        task({ CacheHit: { source: "Remote", saved_duration_ms: -1 } }),
      ],
    }),
  ).toEqual([
    { package: "@team/server", task: "typecheck", source: "remote", savedMs: 1200 },
    { package: "@team/server", task: "typecheck", source: "local", savedMs: 500 },
    { package: "@team/server", task: "typecheck", source: "failed", savedMs: 0 },
    { package: "@team/server", task: "typecheck", source: "executed", savedMs: 0 },
    { package: "@team/server", task: "typecheck", source: "unspecified", savedMs: 999 },
  ]);
});
