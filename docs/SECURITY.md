# Security and data handling

- Secret material is provided by environment and excluded from Git. JWT startup requires at least 32 characters.
- Use TLS/secure cookies in deployment. COOKIE_SECURE=false is only for local HTTP testing.
- Browser traffic goes through the Next.js same-origin API rewrite. APP_ORIGIN must exactly match the frontend origin. Requests from other browser origins are rejected. Do not add permissive CORS.
- JWT access expiry is 15 minutes; rotating refresh cookies expire after seven days. Refresh rows are locked before rotation on PostgreSQL. Logout revokes the refresh token; an already issued access JWT may remain valid until expiry.
- Every protected request checks current user and school activation. Teachers are restricted by class and subject. Platform users cannot use student or teacher APIs.
- Student payloads exclude answer keys; unreleased grades and feedback are hidden. Duplicate event IDs return the original submission, with ownership verification.
- Objective quizzes are graded on the server. Submission transactions lock the student row on PostgreSQL to serialize attempt limits.
- Login and demo-form rate limits are per process. Multi-instance deployments need shared limits and trusted proxy configuration.
- Offline lessons, drafts and attachments persist in plaintext IndexedDB. Use separate managed profiles. Do not clear site data until pending work has synchronized; stronger offline user verification/encryption is required before shared-device production use.
- The initial migration imports model metadata. Freeze explicit migration operations before evolving the production schema.
- Backups, retention policies, guardian consent, incident response and Ghana data-protection review must be resolved before using real learner data.

Uploads use a private bucket and school-scoped object keys. Download handlers recheck authorization; parent accounts cannot access resource or student-management APIs. Student-work file IDs are validated against the authenticated student and assessment before being attached. Office archive inspection and signatures are not antivirus scanning. CSV exports neutralize formula prefixes. School reports do not expose unreleased grades.
