import * as NodeServices from "@effect/platform-node/NodeServices";
import { assert, it } from "@effect/vitest";
import { DEFAULT_SIGNAL_EXPORT } from "@t3tools/shared/observability";
import * as OtelEnvironment from "@t3tools/shared/otelEnvironment";
import * as Effect from "effect/Effect";
import * as Layer from "effect/Layer";
import { HttpClient, HttpClientError, HttpClientResponse } from "effect/http";
import { describe } from "vite-plus/test";

import * as ServerConfig from "../config.ts";
import * as OtlpEndpointCheck from "./OtlpEndpointCheck.ts";

interface PostedRequest {
  readonly url: string;
  readonly headers: Readonly<Record<string, string>>;
  readonly body: string;
  readonly signal: AbortSignal;
}

const checkWith = (
  status: number | null,
  overrides: Partial<ServerConfig.ServerConfig["Service"]> = {},
  httpClientLayer?: Layer.Layer<HttpClient.HttpClient>,
) => {
  const requests: Array<PostedRequest> = [];
  const httpClient = HttpClient.make((request, _url, signal) => {
    requests.push({
      url: request.url,
      headers: request.headers,
      body: request.body._tag === "Uint8Array" ? new TextDecoder().decode(request.body.body) : "",
      signal,
    });
    return status === null
      ? Effect.fail(
          new HttpClientError.HttpClientError({
            reason: new HttpClientError.TransportError({ request }),
          }),
        )
      : Effect.succeed(HttpClientResponse.fromWeb(request, new Response(null, { status })));
  });
  const configLayer = Layer.effect(
    ServerConfig.ServerConfig,
    Effect.gen(function* () {
      const config = yield* ServerConfig.ServerConfig;
      return ServerConfig.make({ ...config, ...overrides });
    }),
  ).pipe(Layer.provide(ServerConfig.layerTest(process.cwd(), { prefix: "t3-otlp-check-" })));
  const layer = OtlpEndpointCheck.layer.pipe(
    Layer.provide(httpClientLayer ?? Layer.succeed(HttpClient.HttpClient, httpClient)),
    Layer.provide(configLayer),
    Layer.provide(NodeServices.layer),
  );
  return { requests, layer };
};

const check = (input: Parameters<OtlpEndpointCheck.OtlpEndpointCheck["Service"]["check"]>[0]) =>
  Effect.gen(function* () {
    const service = yield* OtlpEndpointCheck.OtlpEndpointCheck;
    return yield* service.check(input);
  });

describe("OtlpEndpointCheck", () => {
  it.effect(
    "never probes any endpoint, including explicitly configured endpoints with credentials",
    () => {
      const signalExport = { ...DEFAULT_SIGNAL_EXPORT, headers: { "x-api-key": "secret" } };
      const { requests, layer } = checkWith(200, {
        otlpTracesUrl: "https://collector.example/v1/traces",
        otlpMetricsUrl: "https://collector.example/v1/metrics",
        otlpLogsUrl: "https://collector.example/v1/logs",
        otlpTracesExport: signalExport,
        otlpMetricsExport: signalExport,
        otlpLogsExport: signalExport,
        otelEnvironment: { ...OtelEnvironment.none, disabled: false },
      });
      return Effect.gen(function* () {
        for (const signal of ["traces", "metrics", "logs"] as const) {
          for (const url of [
            `https://collector.example/v1/${signal}`,
            "https://other.example/collect",
          ]) {
            assert.deepStrictEqual(yield* check({ signal, url }), {
              _tag: "Unreachable",
              timedOut: false,
            });
          }
        }
        assert.lengthOf(requests, 0);
      }).pipe(Effect.provide(layer));
    },
  );
});
