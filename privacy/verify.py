#!/usr/bin/env python3
import argparse
import os
from pathlib import Path
from privacy_tools import manifest, check_kit, check_payload, check_source_delta, run

TESTS = [
    "packages/shared/src/otelEnvironment.test.ts",
    "packages/shared/src/relayTracing.test.ts",
    "apps/server/src/telemetry/AnalyticsService.test.ts",
    "apps/server/src/observability/OtlpEndpointCheck.test.ts",
    "packages/provider-core/src/server/instanceEnvironment.test.ts",
    "packages/client-runtime/src/authorization/remote.test.ts",
    "apps/mobile/src/features/observability/noTelemetry.test.ts",
    "apps/mobile/src/features/observability/tracing.test.ts",
    "infra/task-cache/src/telemetry.test.ts",
    "infra/task-cache/src/Cache.test.ts",
    "infra/relay/src/mobileTelemetry/MobileTelemetry.test.ts",
    "packages/provider-pi/src/server/rollback.test.ts",
    "packages/shared/src/markdownPipeline.test.ts",
    "apps/mobile/src/lib/markdownHtml.test.ts",
    "apps/web/src/markdown/wordsHast.test.ts",
    "apps/desktop/src/wsl/DesktopWslEnvironment.test.ts",
]

PACKAGES = ["packages/shared", "packages/provider-core", "packages/client-runtime",
            "apps/server", "apps/web", "apps/desktop", "apps/mobile", "infra/relay", "infra/task-cache", "packages/provider-pi"]


def verify(repo):
    config = manifest()
    check_kit(config)
    check_payload(repo, config)
    check_source_delta(repo, config)
    env = {**os.environ, "VP_REMOTE_CACHE": "off", "VP_REMOTE_CACHE_URL": "",
           "T3_TASK_CACHE_TELEMETRY": "off", "T3CODE_TELEMETRY_ENABLED": "false",
           "OTEL_SDK_DISABLED": "true", "CLERK_TELEMETRY_DISABLED": "1",
           "DO_NOT_TRACK": "1", "CI": "true", "NODE_OPTIONS": ""}
    vp = repo / "node_modules/.bin/vp"
    tsgo = repo / "node_modules/.bin/effect-tsgo"
    run([vp, "test", "run", *TESTS], repo, env=env)
    changed_ts = [p for p in config["patched_files"] if p.endswith((".ts", ".tsx"))]
    run([vp, "lint", *changed_ts], repo, env=env)
    for package in PACKAGES:
        run([tsgo, "tsrs", "--noEmit"], repo / package, env=env)
    check_payload(repo, config)
    check_source_delta(repo, config)
    print("PASS: privacy boundaries, scoped tests/lint and affected package typechecks")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", type=Path, nargs="?", default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    verify(args.repo.resolve())
