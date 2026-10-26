# Render + Neon deployment

The repository contains a two-service `render.yaml`. No database credentials are included.

1. Create a dedicated Neon project/branch for EduMate. Use a PostgreSQL connection URL with `sslmode=require`. Do not reuse a different application's production database.
2. Open https://dashboard.render.com/blueprint/new?repo=https://github.com/kwaw-ebn/edumate-ghana and select the intended workspace.
3. Set backend DATABASE_URL to the Neon connection URL, DEMO_PASSWORD to a strong demo password, APP_ORIGIN to the exact frontend origin, and frontend API_ORIGIN to the backend's public HTTPS origin.
4. Both services use free web plans in Frankfurt. Confirm availability in your account. Cold starts may affect demonstrations. If service names receive a different actual URL, use that URL in APP_ORIGIN/API_ORIGIN.
5. The backend runs Alembic on startup (single instance only for this demo). Production deployments should run migrations as one controlled release task using a direct Neon URL. For a pooled runtime connection, provide the direct URL during the migration step.
6. After the backend is healthy, seed the fictional demo explicitly using `python -m app.seed` in the backend environment. If a shell is unavailable on your chosen plan, run this locally with the same Neon DATABASE_URL and DEMO_PASSWORD in a secure environment.
7. Build/deploy the frontend after API_ORIGIN is set; Next rewrites are resolved during build.
8. Verify backend `/health`, frontend landing page, each demo role, lesson publication, assignment submission, feedback release and enquiries. Check persisted results after logout/login and redeploy.
9. Download a lesson, wait for the service worker to activate, disconnect in the browser and reload. Confirm downloaded text is shown. This does not test offline quizzes or sync, which are not implemented.

Build configuration is provided, but Render CLI validation and live deployment must be recorded when performed. Do not mark the full acceptance criteria complete based on this file.
