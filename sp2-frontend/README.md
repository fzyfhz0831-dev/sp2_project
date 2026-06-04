# SP2-Frontend

SpireInsight frontend MVP built with Vue 3 and Vite.

## Frontend Data Mode

The frontend currently supports two data modes through Vite environment variables.

### Local Mode

Local mode is the default. It reads insights from:

```text
/data/run_insights.json
```

Use this mode for local development, static previews, and the current MVP.

### Remote Mode

Remote mode fetches insights from `VITE_INSIGHTS_API_URL`. If the remote request fails, the app automatically falls back to the local JSON file.

No real API URL is hardcoded in the app.

### Environment Setup

Copy `.env.example` to `.env` and adjust values as needed:

```text
VITE_INSIGHTS_API_MODE=local
VITE_INSIGHTS_API_URL=
```

For remote mode:

```text
VITE_INSIGHTS_API_MODE=remote
VITE_INSIGHTS_API_URL=https://your-api.example.com/insights
```

If `VITE_INSIGHTS_API_MODE` is not `remote`, the frontend uses local mode.
