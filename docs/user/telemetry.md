# Privacy fork: telemetry disabled

This fork disables product analytics, install/owner analytics delivery, anonymous agent feedback delivery,
relay tracing, OTLP trace/metric/log export (including endpoint probes), and mobile crash/startup
reporting at source level. Environment variables, saved settings, managed policies and the diagnostics
switches cannot re-enable these exporters. The build-task collector and old-queue flusher are also
inert. Clerk telemetry is disabled independently of normal sign-in.

Local logs, local trace files, CPU/memory resource diagnostics and normal provider usage accounting
remain available. Model requests, authentication, update checks, source control, remote sessions and
explicitly enabled mobile notifications remain functional network features, not telemetry opt-outs.
In particular, **Publish agent activity** still sends activity details to the relay for notifications.
Disable that feature separately if you do not want this functional data transfer.

Provider processes receive common telemetry opt-out variables after user-configured environment
values. These are defense in depth, not control over arbitrary external binaries: provider CLIs,
extensions, MCP servers and remote services may have their own reporting and retention policies.
A self-built client cannot disable logs collected by the official hosted relay or model APIs.

Use builds from the patched source. Installing an official release (including through the normal
updater) replaces this privacy policy with upstream behavior. Existing files and queues from older
versions are not deleted; this fork does not transmit them. Explicit feedback reports can still be
saved locally, but the disabled analytics service never queues or delivers them. Mobile native builds must be regenerated
and rebuilt so expo-observe is absent from autolinking; an over-the-air JS update alone is insufficient.

This is a source-level privacy policy, not a claim that the application makes zero network requests.
