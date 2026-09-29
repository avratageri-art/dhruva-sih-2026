# DHRUVA Frontend

This directory contains the existing React dashboard for DHRUVA. Internal package and path names retain legacy identifiers where changing them would risk compatibility.

## Run

Requires Node.js 20.19 or newer.

```bash
npm ci
npm run dev
```

Open <http://localhost:5173>. Start the FastAPI backend on <http://localhost:8000> first.

## Build

```bash
npm run build
```

The active entry point is `src/main.jsx`, which loads `src/App.jsx`. The current package does not define a lint or browser-test script. Do not put secrets in `VITE_*` variables; those values are exposed to browser code.

See the repository [README](../README.md) and [local setup guide](../docs/development/local-setup.md) for the complete stack.
