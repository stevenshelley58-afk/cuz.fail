import { createServer } from "node:http";
import { createReadStream, existsSync, statSync } from "node:fs";
import { join, normalize, resolve, sep } from "node:path";
import { spawn } from "node:child_process";

const distDir = resolve("dist");
const checkoutUrl = "https://buy.stripe.com/lotfile_ci_fixture";

function contentType(path) {
  if (path.endsWith(".html")) return "text/html; charset=utf-8";
  if (path.endsWith(".js")) return "text/javascript; charset=utf-8";
  if (path.endsWith(".css")) return "text/css; charset=utf-8";
  if (path.endsWith(".svg")) return "image/svg+xml";
  if (path.endsWith(".ico")) return "image/x-icon";
  return "application/octet-stream";
}

function safeDistPath(urlPath) {
  const decodedPath = decodeURIComponent(urlPath.split("?", 1)[0]);
  const relative = normalize(decodedPath.replace(/^\/+/, ""));
  const candidate = resolve(distDir, relative);
  if (candidate !== distDir && !candidate.startsWith(`${distDir}${sep}`)) return null;
  return candidate;
}

function serveFile(path, res) {
  res.writeHead(200, { "content-type": contentType(path) });
  createReadStream(path).pipe(res);
}

const server = createServer((req, res) => {
  const url = req.url ?? "/";
  if (url === "/api/v1/health" || url === "/api/v1/ready") {
    res.writeHead(200, { "content-type": "application/json" });
    res.end(JSON.stringify({ status: "ok" }));
    return;
  }

  const requested = safeDistPath(url);
  if (requested && existsSync(requested) && statSync(requested).isFile()) {
    serveFile(requested, res);
    return;
  }

  const directoryIndex = requested ? join(requested, "index.html") : null;
  if (directoryIndex && existsSync(directoryIndex) && statSync(directoryIndex).isFile()) {
    serveFile(directoryIndex, res);
    return;
  }

  const indexPath = join(distDir, "index.html");
  if (existsSync(indexPath)) {
    serveFile(indexPath, res);
    return;
  }

  res.writeHead(404, { "content-type": "text/plain; charset=utf-8" });
  res.end("dist/index.html missing");
});

function closeServer() {
  return new Promise((resolve, reject) => {
    server.close((err) => (err ? reject(err) : resolve()));
  });
}

function runVerifier(origin) {
  return new Promise((resolveRun, rejectRun) => {
    let stdout = "";
    let stderr = "";
    const child = spawn(
      process.execPath,
      ["scripts/verify-live-launch.mjs", "--strict", "--json"],
      {
        cwd: process.cwd(),
        env: {
          ...process.env,
          LAUNCH_ORIGIN: origin,
          LIVE_CHECKOUT_URL: checkoutUrl,
        },
        stdio: ["ignore", "pipe", "pipe"],
      },
    );
    child.stdout.on("data", (chunk) => {
      stdout += chunk;
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk;
    });
    child.on("error", rejectRun);
    child.on("exit", (code) => {
      if (code !== 0) {
        rejectRun(new Error(`verify-live-launch exited with ${code}\n${stderr}${stdout}`));
        return;
      }
      let result;
      try {
        result = JSON.parse(stdout);
      } catch (err) {
        rejectRun(new Error(`verify-live-launch did not emit JSON: ${err instanceof Error ? err.message : String(err)}\n${stdout}`));
        return;
      }
      if (result.status !== "passed") {
        rejectRun(new Error(`verify-live-launch JSON status was ${result.status}`));
        return;
      }
      for (const route of ["/", "/privacy", "/terms", "/app"]) {
        if (result.evidence.routes[route]?.status !== 200) {
          rejectRun(new Error(`missing JSON route evidence for ${route}`));
          return;
        }
      }
      if (result.evidence.api["/api/v1/ready"]?.service_status !== "ok") {
        rejectRun(new Error("missing JSON ready evidence"));
        return;
      }
      resolveRun();
    });
  });
}

if (!existsSync(join(distDir, "index.html"))) {
  console.error("web/dist is missing. Run npm run build before test:live-launch-preview.");
  process.exit(1);
}

await new Promise((resolveListen) => server.listen(0, "127.0.0.1", resolveListen));
try {
  const address = server.address();
  const port = typeof address === "object" && address ? address.port : 0;
  await runVerifier(`http://127.0.0.1:${port}`);
} finally {
  await closeServer();
}

console.log("live launch preview test passed");
