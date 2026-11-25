import type { ProviderInstanceEnvironment } from "@t3tools/contracts";
import { stripAppImageRuntimeEnv } from "@t3tools/shared/appImageRuntimeEnv";
import * as HostProcess from "@t3tools/shared/HostProcess";
import * as Effect from "effect/Effect";

import { expandHomeVariable } from "./pathExpansion.ts";

const withoutTelemetry = (env: NodeJS.ProcessEnv): NodeJS.ProcessEnv => {
  const disabled: Record<string, string> = {
    DO_NOT_TRACK: "1",
    CLERK_TELEMETRY_DISABLED: "1",
    DISABLE_TELEMETRY: "1",
    DISABLE_ERROR_REPORTING: "1",
    OTEL_SDK_DISABLED: "true",
    T3CODE_OTEL_SDK_DISABLED: "true",
    T3CODE_TELEMETRY_ENABLED: "false",
  };
  const next = Object.fromEntries(
    Object.entries(env).filter(([name]) => !Object.hasOwn(disabled, name.toUpperCase())),
  );
  return { ...next, ...disabled };
};

export const mergeProviderInstanceEnvironment = Effect.fn(function* (
  environment: ProviderInstanceEnvironment | undefined,
  baseEnv: NodeJS.ProcessEnv = process.env,
) {
  // Commands the agent runs inherit this env; the AppImage mount's libraries would shadow the system's.
  const hostEnv = stripAppImageRuntimeEnv(baseEnv);
  if (!environment || environment.length === 0) {
    return withoutTelemetry(hostEnv);
  }

  const home = yield* HostProcess.HomeDirectory;
  const windows = (yield* HostProcess.Platform) === "win32";
  const next: NodeJS.ProcessEnv = { ...hostEnv };
  for (const variable of environment) {
    // An unresolved secret reference carries no value; the registry resolves it for the provider.
    if (typeof variable.value !== "string") continue;
    // Windows reads names without regard to case, and a child gets the first spelling in sort
    // order. Upper case sorts first, so the configured value wins even where a spawn merges the
    // parent environment back in.
    const name = windows ? variable.name.toUpperCase() : variable.name;
    if (windows) {
      for (const inherited of Object.keys(next)) {
        if (inherited.toUpperCase() === name) delete next[inherited];
      }
    }
    next[name] = expandHomeVariable(name, variable.value, home);
  }
  return withoutTelemetry(next);
});
