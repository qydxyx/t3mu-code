import { assert, describe, expect, it } from "@effect/vitest";
import * as ConfigProvider from "effect/ConfigProvider";
import * as Effect from "effect/Effect";
import { DEFAULT_SIGNAL_EXPORT } from "./observability.ts";
import * as Otel from "./otelEnvironment.ts";

it.effect.each([
  {},
  { T3CODE_TELEMETRY_ENABLED: "true" },
  { T3CODE_OTEL_SDK_DISABLED: "false", OTEL_SDK_DISABLED: "false" },
  { OTEL_EXPORTER_OTLP_ENDPOINT: "https://collector.example" },
  { T3CODE_TELEMETRY_ENABLED: "true", CI: "true", OTEL_TRACES_EXPORTER: "otlp" },
])("never enables exports, regardless of environment (%j)", (env) =>
  Effect.gen(function* () {
    const otel = yield* Otel.load.pipe(
      Effect.provide(ConfigProvider.layer(ConfigProvider.fromEnvRecord(env))),
    );
    expect(otel.disabled).toBe(true);
    expect(Otel.isRelayTracingEnabled(env)).toBe(false);
    for (const signal of ["traces", "metrics", "logs"] as const) {
      expect(
        Otel.resolveSignalEndpoint(
          { ...otel, disabled: false },
          signal,
          { url: "https://explicit.example", export: DEFAULT_SIGNAL_EXPORT },
          { bootstrapUrl: "https://bootstrap.example", settingsUrl: "https://saved.example" },
        ),
      ).toBeUndefined();
    }
  }),
);

describe("isCiEnvironment", () => {
  it("treats a set CI variable as CI, except empty, false, and 0", () => {
    assert.isFalse(Otel.isCiEnvironment({}));
    assert.isTrue(Otel.isCiEnvironment({ CI: "1" }));
    assert.isTrue(Otel.isCiEnvironment({ TF_BUILD: "True" }));
    assert.isTrue(Otel.isCiEnvironment({ BITBUCKET_BUILD_NUMBER: "42" }));
    for (const value of ["", " ", "false", "FALSE", "0"]) {
      assert.isFalse(Otel.isCiEnvironment({ CI: value }), `CI=${value}`);
    }
    assert.isTrue(Otel.isCiEnvironment({ CI: "false", GITLAB_CI: "true" }));
  });
});
