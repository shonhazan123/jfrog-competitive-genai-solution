# JFrog Competitive Intelligence

## Run (Docker only)

From this folder:

```bash
docker compose up --build
```

That starts **db**, **api**, **worker**, and **client**. When the containers are up:

- **UI:** http://localhost:5173
- **API:** http://localhost:8000/health

Stop with **Ctrl+C**, then:

```bash
docker compose down
```

To run in the background instead:

```bash
docker compose up --build -d
docker compose logs -f
docker compose down
```

**Do not** run `npm run dev` in `client/` on your machine — use only Docker. A local Vite on port 5173 will look like the app is up even after `docker compose down`, but the API will be gone.
