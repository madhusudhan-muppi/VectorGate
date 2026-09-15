# VectorGate Dashboard

React/Vite Stage 4 dashboard for the live VectorGate API.

```powershell
npm install
Copy-Item .env.example .env
npm run dev
```

The dashboard expects the Stage 3 backend at `VITE_API_BASE_URL` and polls health every 10 seconds and operational data every 4 seconds. Production output is created with `npm run build`.

The map uses OpenStreetMap tiles with attribution. Nodes at `0,0` are treated as synthetic placeholders and withheld from the geographic map. Activity colors are prototype relative thresholds: 0 quiet, 1-4 normal, 5-9 elevated, and 10+ high.
