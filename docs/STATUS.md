# EduMate Ghana implementation status

## Implemented school expansion

| Requested area | Available behavior |
|---|---|
| Teacher uploads | Private S3-compatible storage. Attach PDF, DOCX, PPTX, XLSX, PNG and JPEG resources to lessons or assessments. Download access follows school, class, subject and student-work ownership. File extension, contents and size are checked; 10 MB limit. |
| Assignment drafts and attachments | Local autosave plus versioned server drafts. Photos and worksheet attachments accompany final submissions. Conflicts preserve local work and allow comparison with the server draft. Teachers can download attachments for marking. |
| Offline learning | Cached standalone workspace, downloaded lessons/resources, ungraded practice, downloaded assessments, local answers/photos, persistent queue and automatic synchronization on reconnection or periodic online checks. Failed/expired sessions retain work. Server rechecks access and attempt limits and prevents duplicate final submissions. |
| Ghana curriculum organization | School-defined terms, week, strand, sub-strand and objectives. School administrator can record educator review. Teachers author ungraded offline practice questions. No official NaCCA approval is claimed. |
| Performance reports | Authorized class/subject filters, released average scores, lesson completion, assignment completion and clearly defined follow-up flags. Download CSV and paginated PDF. |
| Flexible school setup | Create classes, subjects and academic terms; register learners, teachers and parents; assign teachers; enroll/transfer learners with term history. Current content access follows the learner's current class. |
| Parent summaries | School-created parent accounts linked to named learners. Parents see only linked learners' released scores, feedback, lesson completion and outstanding current-class assignments. No automatic email or messaging is enabled. |
| Device records | Register tablet asset tags, assign learners, change active status and record app heartbeats/last synchronization. Inactive records reject heartbeats. This is app inventory, not Android kiosk/remote-lock software. |

Core lesson publication, server-scored quizzes, teacher grading, marketing page and stored demonstration enquiries remain available.

## Verification

- Backend tests cover the original workflow plus setup/enrollment, private attachments and validation, draft conflict handling, synchronization idempotence and permission rechecks, parent restrictions, device activation, and PDF/CSV exports.
- Production Next.js build and TypeScript checks pass.
- Real Chromium tablet-browser test covers online draft restoration, disconnected navigation and downloaded lesson/practice access, offline answers/photo persistence after reload, work retention after session expiry, upload and synchronization after reconnection, and duplicate synchronization.
- Tablet screenshots and the generated school report were visually inspected.
- Additive table DDL was exercised on an isolated Neon branch. SQLite migration from the previous schema was also verified. Direct PostgreSQL TCP access from the development environment is unavailable; live checks use the deployed API and the Neon connector.
- Deployed services: https://edumate-ghana.onrender.com and https://edumate-ghana-api.onrender.com. Deployment environment variables are managed directly on Render; `render.yaml` is a template, not a second live management path.

## Remaining limitations

- Offline data is plaintext in the browser profile. Use a separate, managed profile per learner. Logout removes the active offline profile marker while retaining unsynchronized data. Encryption/PIN-based offline access is not implemented.
- Ungraded lesson practice reveals its answers for immediate offline feedback. Formal quiz answers stay on the server. Formal work is scored/recorded only after synchronization; server receipt time determines lateness, and changed permissions or exhausted attempt limits can reject queued work without deleting it locally.
- An enrollment changes one current class. Historical term enrollment is retained, but report filtering currently uses the learner's current class rather than reconstructing historical class rosters.
- Uploads check document signatures and office archives but do not include antivirus scanning. Office documents are downloaded for compatible viewers, not rendered inside the app. No storage quota/billing dashboard or retention automation yet.
- Rich-text/math editing, scheduled assessments, timers, advanced charts, notifications, subscription billing, platform school-admin provisioning and password-reset email remain outside this expansion.
- Reports use released attempts and equal learner weighting for the class average. Follow-up flags are thresholds, not educational diagnoses.
- Device activity requires the learner to select their assigned tablet record in Offline learning. Inactive inventory status does not lock, wipe or uninstall software on Android.
- Content is original demonstration material requiring educator curriculum review before real school use. Some original seed quiz questions repeat.
- Stronger session-family replay handling, distributed rate limits, privacy/retention policies and real Android device testing remain production preparation work.

## Live release verification - 26 October 2026

Release commit `cacb658143d35585f6c234fb4b76ab3acd8ce7e5` is live on both existing Render services. Neon migration `0002` completed and the private resource bucket is configured.

Live API checks passed: real private-object upload/download; curriculum review and downloadable practice packages; versioned drafts and conflict rejection; submission attachments and released feedback; synchronization retries without duplicate submissions; device last-sync recording; linked-parent isolation; custom classes/subjects/terms; and school PDF/CSV exports. The checks used fictional records and added one demonstration worksheet lesson and assignment.

The parent demonstration login is `parent@demo.edumate.test`, linked to Ama, using the existing configured demonstration password. See [school tool instructions](SCHOOL_TOOLS.md).

## Tutor frontend expansion

The student tutor interface now supports a published-lesson entry point, subject/lesson context, chat, prepared explanations and hints, teacher-authored or sample ungraded practice with feedback/retry, revision plans, optional browser read-aloud and per-lesson tab history. All screens identify demonstration mode. GPT is not connected and there are no AI requests or paid API dependencies. See [tutor frontend and future integration](AI_TUTOR.md).
