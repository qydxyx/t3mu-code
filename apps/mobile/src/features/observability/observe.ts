export const crashReportingAvailable = false;

export async function setCrashReportsEnabled(_enabled: boolean): Promise<void> {}

export const Observe = { reportError: (_error: unknown): void => {} };
