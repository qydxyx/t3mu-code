import * as NodeHttpPlatform from "@effect/platform-node/NodeHttpPlatform";
import * as NodeServices from "@effect/platform-node/NodeServices";
import { expect, it } from "@effect/vitest";
import { RelayApi } from "@t3tools/contracts/relay";
import * as Deferred from "effect/Deferred";
import * as Effect from "effect/Effect";
import * as Layer from "effect/Layer";
import * as Redacted from "effect/Redacted";
import * as Etag from "effect/http/Etag";
import * as HttpClient from "effect/http/HttpClient";
import type * as HttpClientError from "effect/http/HttpClientError";
import type * as HttpClientRequest from "effect/http/HttpClientRequest";
import * as HttpClientResponse from "effect/http/HttpClientResponse";
import * as HttpEffect from "effect/http/HttpEffect";
import * as HttpRouter from "effect/http/HttpRouter";
import * as HttpServerRequest from "effect/http/HttpServerRequest";
import * as HttpServerResponse from "effect/http/HttpServerResponse";
import * as HttpApi from "effect/http-api/HttpApi";
import * as HttpApiBuilder from "effect/http-api/HttpApiBuilder";

import { RELAY_HTTP_ROUTER_CONFIG } from "../http/Api.ts";
import * as RelayHttpApi from "../http/Api.ts";
import * as MobileTelemetry from "./MobileTelemetry.ts";

const PROJECT_ID = "d763fcb8-d37c-41ea-a773-b54a0ab4a454";
const destinations = {
  traces: { url: "https://axiom.test/v1/traces", dataset: "mobile-traces" },
  logs: { url: "https://axiom.test/v1/logs", dataset: "mobile-logs" },
  metrics: { url: "https://axiom.test/v1/metrics", dataset: "mobile-metrics" },
} as const;

interface Harness {
  readonly execute?: (
    request: HttpClientRequest.HttpClientRequest,
  ) => Effect.Effect<HttpClientResponse.HttpClientResponse, HttpClientError.HttpClientError>;
  /** The source maps bucket, by key. */
  readonly objects?: Readonly<Record<string, string>>;
}

const makeHarness = (options: Harness = {}) => {
  const sent: Array<HttpClientRequest.HttpClientRequest> = [];
  const execute =
    options.execute ??
    ((request: HttpClientRequest.HttpClientRequest) =>
      Effect.succeed(
        HttpClientResponse.fromWeb(
          request,
          new Response("{}", { status: 200, headers: { "content-type": "application/json" } }),
        ),
      ));
  const layerTelemetry = MobileTelemetry.layer.pipe(
    Layer.provide(
      Layer.mergeAll(
        Layer.succeed(MobileTelemetry.MobileTelemetrySettings, {
          axiomToken: Redacted.make("axiom-ingest-token"),
          destinations,
        }),
        Layer.succeed(MobileTelemetry.MobileTelemetryRateLimiter, {
          allow: () => Effect.succeed(true),
        }),
        MobileTelemetry.layerSourceMaps.pipe(
          Layer.provide(
            Layer.succeed(MobileTelemetry.SourceMapObjects, {
              get: (key) =>
                Effect.sync(() => {
                  const object = options.objects?.[key];
                  return object === undefined
                    ? undefined
                    : { size: object.length, text: Effect.succeed(object) };
                }),
            }),
          ),
        ),
        Layer.succeed(
          HttpClient.HttpClient,
          HttpClient.make((request) => {
            sent.push(request);
            return execute(request);
          }),
        ),
      ),
    ),
  );
  const httpEffect = HttpRouter.toHttpEffect(
    Layer.mergeAll(
      HttpApiBuilder.layer(HttpApi.make("RelayApi").add(RelayApi.groups.mobileTelemetry)).pipe(
        Layer.provide(MobileTelemetry.layerApi.pipe(Layer.provide(layerTelemetry))),
        Layer.provide([NodeServices.layer, NodeHttpPlatform.layer, Etag.layerWeak]),
      ),
      RelayHttpApi.layerNotFoundRoute,
    ),
  ).pipe(Effect.provideService(HttpRouter.RouterConfig, RELAY_HTTP_ROUTER_CONFIG));
  const send = (request: Request) =>
    Effect.gen(function* () {
      const handler = yield* httpEffect;
      const response = yield* Deferred.make<HttpServerResponse.HttpServerResponse>();
      yield* HttpEffect.toHandled(handler, (_request, value) =>
        Deferred.succeed(response, value),
      ).pipe(
        Effect.provideService(
          HttpServerRequest.HttpServerRequest,
          HttpServerRequest.fromWeb(request),
        ),
      );
      return yield* Deferred.await(response);
    });
  return { sent, send };
};

const ingest = (signal: string, body: string) =>
  new Request(`https://relay.test/v1/mobile/observe/${PROJECT_ID}/v1/${signal}`, {
    method: "POST",
    headers: { "content-type": "application/json", "cf-connecting-ip": "203.0.113.7" },
    body,
  });

it.effect("drops crash, startup, trace and metric payloads without forwarding", () => {
  const { sent, send } = makeHarness();
  return Effect.gen(function* () {
    for (const signal of ["logs", "traces", "metrics"]) {
      const response = yield* send(ingest(signal, '{"private":"must stay local"}'));
      expect(response.status).toBe(204);
    }
    expect(sent).toHaveLength(0);
  }).pipe(Effect.scoped);
});
