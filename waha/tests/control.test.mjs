import assert from "node:assert/strict";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, test } from "node:test";
import { createControlServer } from "../control.mjs";

const servers = [];

afterEach(async () => {
  await Promise.all(
    servers.splice(0).map(
      (server) => new Promise((resolve) => server.close(resolve)),
    ),
  );
});

async function fixture(fetchImpl, allowDirect = true) {
  const dir = mkdtempSync(join(tmpdir(), "waha-control-"));
  const htmlPath = join(dir, "index.html");
  writeFileSync(htmlPath, "<h1>WAHA</h1>");
  const { server } = createControlServer({
    apiUrl: "http://waha.test:3000",
    apiKey: "test-secret-key-123",
    sessionName: "default",
    htmlPath,
    allowDirect,
    fetchImpl,
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  servers.push(server);
  const address = server.address();
  return `http://127.0.0.1:${address.port}`;
}

test("blocks control access outside Home Assistant ingress", async () => {
  const base = await fixture(async () => new Response("{}"), false);
  const response = await fetch(`${base}/control/overview`);
  assert.equal(response.status, 403);
});

test("serves the ingress root when Supervisor sends a double slash", async () => {
  const base = await fixture(async () => new Response("{}"));
  const response = await fetch(`${base}//`);
  assert.equal(response.status, 200);
  assert.equal(await response.text(), "<h1>WAHA</h1>");
});

test("overview calls WAHA with the configured API key", async () => {
  const requests = [];
  const base = await fixture(async (url, init) => {
    requests.push({ url: String(url), key: init.headers.get("X-Api-Key") });
    if (String(url).includes("/api/sessions")) return Response.json([]);
    if (String(url).includes("/api/version")) return Response.json({ version: "2026.7.1", engine: "GOWS" });
    return Response.json({ uptime: 10 });
  });
  const response = await fetch(`${base}/control/overview`);
  const body = await response.json();
  assert.equal(response.status, 200);
  assert.equal(body.version.version, "2026.7.1");
  assert.equal(requests.length, 3);
  assert.ok(requests.every((request) => request.key === "test-secret-key-123"));
});

test("session actions are restricted and forwarded", async () => {
  let calledUrl;
  const base = await fixture(async (url) => {
    calledUrl = String(url);
    return Response.json({ status: "ok" });
  });
  const response = await fetch(`${base}/control/session/default/restart`, { method: "POST" });
  assert.equal(response.status, 200);
  assert.equal(calledUrl, "http://waha.test:3000/api/sessions/default/restart");
  const invalid = await fetch(`${base}/control/session/default/logout`, { method: "POST" });
  assert.equal(invalid.status, 404);
});
