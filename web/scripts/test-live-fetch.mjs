import assert from "node:assert/strict";
import { createServer } from "node:http";
import { fetchText } from "./live-fetch.mjs";

const server = createServer((req, res) => {
  if (req.url === "/ok") {
    res.writeHead(200, { "content-type": "text/plain" });
    res.end("local preview ok");
    return;
  }
  res.writeHead(404, { "content-type": "text/plain" });
  res.end("missing");
});

await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
try {
  const address = server.address();
  const port = typeof address === "object" && address ? address.port : 0;
  const response = await fetchText(`http://127.0.0.1:${port}/ok`, { timeout: 1_000 });

  assert.equal(response.status, 200);
  assert.equal(response.text, "local preview ok");
  assert.equal(response.url, `http://127.0.0.1:${port}/ok`);

  await assert.rejects(
    () => fetchText("ftp://127.0.0.1/unsupported", { timeout: 1_000 }),
    /unsupported launch URL protocol: ftp:/,
  );
} finally {
  await new Promise((resolve, reject) => {
    server.close((err) => (err ? reject(err) : resolve()));
  });
}

console.log("live fetch tests passed");
