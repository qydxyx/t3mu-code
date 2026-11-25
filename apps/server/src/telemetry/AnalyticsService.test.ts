import { expect, it } from "@effect/vitest";
import * as ConfigProvider from "effect/ConfigProvider";
import * as Effect from "effect/Effect";
import * as Analytics from "./AnalyticsService.ts";

it.effect(
  "drops ordinary, feedback and owner events without acquiring identity or HTTP services",
  () =>
    Effect.gen(function* () {
      const analytics = yield* Analytics.make;
      expect(yield* analytics.record("client.turn.requested", { model: "test" })).toBe(false);
      expect(
        yield* analytics.record("agent.feedback", { expected: "private" }, { anonymous: true }),
      ).toBe(false);
      yield* analytics.recordOwners([], "client");
      yield* analytics.flush;
    }).pipe(
      Effect.provide(
        ConfigProvider.layer(ConfigProvider.fromEnvRecord({ T3CODE_TELEMETRY_ENABLED: "true" })),
      ),
    ),
);
