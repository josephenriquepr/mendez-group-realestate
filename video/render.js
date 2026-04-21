'use strict';

/**
 * render.js — Programmatic Remotion renderer for ListaPro
 *
 * Usage: node render.js <props_file.json> <output.mp4>
 *
 * Emits to stdout:
 *   STATUS:bundling    — before webpack bundle
 *   STATUS:composing   — before selectComposition
 *   STATUS:rendering   — before renderMedia
 *   PROGRESS:<0-100>   — during rendering
 *   STATUS:done        — after successful render
 */

const path = require('path');
const fs   = require('fs');

const [, , propsFile, outputPath] = process.argv;

if (!propsFile || !outputPath) {
  console.error('Usage: node render.js <props_file.json> <output_path.mp4>');
  process.exit(1);
}

if (!fs.existsSync(propsFile)) {
  console.error(`Props file not found: ${propsFile}`);
  process.exit(1);
}

const props = JSON.parse(fs.readFileSync(propsFile, 'utf-8'));

const entryPoint = path.join(__dirname, 'src', 'index.tsx');

async function main() {
  // ── 1. Dynamic imports (CJS-compatible) ─────────────────────────────────
  const { bundle }           = require('@remotion/bundler');
  const { renderMedia, selectComposition } = require('@remotion/renderer');

  // ── 2. Bundle ────────────────────────────────────────────────────────────
  process.stdout.write('STATUS:bundling\n');
  let serveUrl;
  try {
    serveUrl = await bundle({
      entryPoint,
      // Pass through webpack without modification
      webpackOverride: (config) => config,
    });
  } catch (err) {
    process.stderr.write(`Bundle error: ${err.message}\n${err.stack}\n`);
    process.exit(1);
  }

  // ── 3. Select composition ────────────────────────────────────────────────
  process.stdout.write('STATUS:composing\n');
  let composition;
  try {
    composition = await selectComposition({
      serveUrl,
      id: 'PropertyReel',
      inputProps: props,
    });
  } catch (err) {
    process.stderr.write(`Composition error: ${err.message}\n${err.stack}\n`);
    process.exit(1);
  }

  // ── 4. Render ────────────────────────────────────────────────────────────
  process.stdout.write('STATUS:rendering\n');
  try {
    await renderMedia({
      composition,
      serveUrl,
      codec: 'h264',
      outputLocation: outputPath,
      inputProps: props,
      onProgress: ({ progress }) => {
        const pct = Math.min(99, Math.round(progress * 100));
        process.stdout.write(`PROGRESS:${pct}\n`);
      },
      // Suppress verbose logs from Remotion
      verbose: false,
      // Concurrency — keep low for reliability
      concurrency: 1,
    });
  } catch (err) {
    process.stderr.write(`Render error: ${err.message}\n${err.stack}\n`);
    process.exit(1);
  }

  process.stdout.write('STATUS:done\n');
}

main().catch((err) => {
  process.stderr.write(`Unexpected error: ${err.message}\n${err.stack}\n`);
  process.exit(1);
});
