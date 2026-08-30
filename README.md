# JFrog Competitive Intelligence

A competitive-intelligence workspace for JFrog: it gathers public signals about
competitors, market movements and the DevSecOps industry, then presents them as
plain, sourced verdicts. The whole stack — database, API, background worker and
web UI — runs with **one command**.

---

## Step 1 (do this first): add your OpenAI API key

> **Required.** This app's whole purpose is to *gather* competitive
> intelligence, and that gathering runs on OpenAI. **Without an
> `OPENAI_API_KEY` the program cannot collect any information** — the site will
> open but **Run now** cannot fill it. Set the key **before** you start the app.

1. In the project root, create your env file from the template:

   ```bash
   cp .env.example .env          # Windows PowerShell:  copy .env.example .env
   ```

2. Open `.env` and paste your key (get one at
   https://platform.openai.com/api-keys):

   ```
   OPENAI_API_KEY=sk-...your key...
   ```

That's the only setup required. (Email digests are optional and off by default;
to enable them, also set `SMTP_USER` and `SMTP_APP_PASSWORD` — a Gmail app
password — in `.env`.)

---

## Step 2: install & launch (one command)

**Prerequisite:** [Docker Desktop](https://www.docker.com/products/docker-desktop/)
installed and running. Nothing else — no Node, no Python, no Postgres.

From the project root:

```bash
docker compose up --build
```

That builds and starts everything (`db` + `api` + `worker` + `client`). The
first build takes a few minutes; later starts are fast. When it's up:

- **Web UI:** http://localhost:5173
- **API health check:** http://localhost:8000/health → `{"status":"ok"}`

> **Keep this terminal open.** The app runs *only while this command is
> running*. If you close the terminal or press **Ctrl+C**, all four services
> stop — the browser tab may still show the page, but every request will fail
> with `ERR_CONNECTION_REFUSED` because the API is no longer running. To run it
> so it survives closing the terminal, start it detached instead:
> `docker compose up --build -d` (see "Run it in the background" below).

To stop when you're done: press **Ctrl+C** in this terminal, then:

```bash
docker compose down
```

Sanity check that everything is actually up: `docker compose ps` should list
`api`, `client`, `worker` and `db` with status **Up** (and `api` showing
`0.0.0.0:8000->8000`).

> If you started the app *before* adding your key, add it to `.env` now and
> restart so the containers pick it up:
> `docker compose down && docker compose up --build`.

---

## Step 3: first run — click **Run now** to fill the site

On a fresh machine the database is empty, so the UI opens on an **onboarding
screen** that explains this and shows a **Run now** button. With your key in
place from Step 1, everything needed for the first run is ready.

1. Open http://localhost:5173.
2. On the **Today** page, click **▶ Run now**.
3. Three research agents fan out across competitors, market signals and industry
   news. A progress card shows the sweep — it takes a few minutes.
4. The Today, Signals, Industry and Competitors rooms fill in automatically.

---

## Run it in the background (optional)

```bash
docker compose up --build -d     # start detached
docker compose logs -f           # follow logs
docker compose down              # stop
```

---

## Troubleshooting

- **`docker compose up` says the Docker daemon isn't running** — start Docker
  Desktop first and wait until it reports "running".
- **The page shows errors like `ERR_CONNECTION_REFUSED` (in the browser console)
  or "Couldn't start the run — is the API reachable?"** — the containers aren't
  running, so nothing is listening on port 8000. This is **not** a key problem.
  Run `docker compose ps`: if `api` isn't **Up**, start the stack with
  `docker compose up --build` (and keep that terminal open, or use `-d`). Then
  refresh the browser. If `api` keeps exiting, check `docker compose logs api`.
- **Port 5173 or 8000 already in use** — something else is bound to that port.
  Stop it, or change the host port mappings in `docker-compose.yml`
  (e.g. `"5174:5173"`), then re-run.
- **Run now fails with an OpenAI key message** — add a valid `OPENAI_API_KEY` to
  `.env` (Step 1) and restart: `docker compose down && docker compose up --build`.
- **The site looks up even after `docker compose down`** — you may have a
  separate local `npm run dev` running on :5173. Use **only** Docker; a stray
  local Vite shadows the container and won't have the API behind it.
- **Start clean (wipe all gathered data)**:

  ```bash
  docker compose down -v     # -v also removes the database volume
  docker compose up --build
  ```

---

## What's inside

| Service  | What it is                                         | Port |
|----------|----------------------------------------------------|------|
| `client` | React + Vite web UI                                | 5173 |
| `api`    | FastAPI HTTP API                                   | 8000 |
| `worker` | Background scheduler (collection, scoring, digests)| —    |
| `db`     | PostgreSQL 17 with pgvector                        | —    |

Operational details of how the system works live in
[`docs/project-instruction/`](docs/project-instruction/).
