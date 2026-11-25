import { expect, it } from "vite-plus/test";
import { crashReportingAvailable, Observe, setCrashReportsEnabled } from "./observe";
import { connectionTracesEnabled, setConnectionTracesEnabled } from "./diagnosticsSetting";

it("never enables mobile crash reports or connection traces", async () => {
  await setCrashReportsEnabled(true);
  setConnectionTracesEnabled(true);
  Observe.reportError(new Error("private"));
  expect(crashReportingAvailable).toBe(false);
  expect(connectionTracesEnabled()).toBe(false);
});
