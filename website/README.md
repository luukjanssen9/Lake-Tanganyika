# Lake Tanganyika Website

Static React/Vite dashboard for the Lake Tanganyika project results.

## Run Locally

From this folder:

```bash
cd website
npm install
npm run dev
```

Then open the local URL printed by Vite, usually:

```txt
http://127.0.0.1:5173/
```

## Refresh Website Data

The website reads copied CSV, GeoJSON, Markdown, and image files from `public/`.
To refresh those files from the main project outputs:

```bash
npm run sync-data
```

`npm run dev` and `npm run build` both run `sync-data` automatically first.

## Build

```bash
npm run build
```

The production files are written to `dist/`.

## Preview Production Build

```bash
npm run preview
```

## Useful Scripts

- `npm run sync-data` copies current project outputs into `website/public/` and rebuilds `public/data/manifest.json`.
- `npm run dev` refreshes data and starts the local development server.
- `npm run build` refreshes data, type-checks the app, and creates the production build.
- `npm run preview` serves the production build locally.
