import { request as httpRequest } from "node:http";
import { request as httpsRequest } from "node:https";

function requestForUrl(url) {
  const protocol = new URL(url).protocol;
  if (protocol === "http:") return httpRequest;
  if (protocol === "https:") return httpsRequest;
  throw new Error(`unsupported launch URL protocol: ${protocol}`);
}

export function fetchText(url, { timeout = 20_000 } = {}) {
  return new Promise((resolve, reject) => {
    const request = requestForUrl(url);
    const req = request(url, { timeout }, (res) => {
      const chunks = [];
      res.on("data", (chunk) => chunks.push(chunk));
      res.on("end", () => {
        resolve({
          url,
          status: res.statusCode ?? 0,
          headers: res.headers,
          text: Buffer.concat(chunks).toString("utf8"),
        });
      });
    });
    req.on("timeout", () => {
      req.destroy(new Error(`timeout fetching ${url}`));
    });
    req.on("error", reject);
    req.end();
  });
}
