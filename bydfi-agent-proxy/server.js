const fs = require("fs");
const http = require("http");
const path = require("path");
const { URL } = require("url");

const root = __dirname;
const routes = {
  "/api/chat": require("./api/chat/index"),
  "/api/chat/stream": require("./api/chat/stream")
};

const mimeTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".ico": "image/x-icon"
};

function decorateResponse(res) {
  res.status = (code) => {
    res.statusCode = code;
    return res;
  };
  res.json = (payload) => {
    if (!res.headersSent) {
      res.setHeader("Content-Type", "application/json; charset=utf-8");
    }
    res.end(JSON.stringify(payload));
  };
  return res;
}

function serveStatic(req, res, pathname) {
  const cleanPath = pathname === "/" ? "/index.html" : pathname;
  const filePath = path.join(root, cleanPath.replace(/^\/+/, ""));
  const resolved = path.resolve(filePath);
  if (!resolved.startsWith(path.resolve(root))) {
    res.status(403).end("Forbidden");
    return;
  }

  fs.readFile(resolved, (error, content) => {
    if (error) {
      res.status(error.code === "ENOENT" ? 404 : 500).end(error.code === "ENOENT" ? "Not found" : "Read failed");
      return;
    }
    const ext = path.extname(resolved).toLowerCase();
    res.status(200);
    res.setHeader("Content-Type", mimeTypes[ext] || "application/octet-stream");
    res.end(content);
  });
}

const server = http.createServer(async (req, res) => {
  decorateResponse(res);
  const requestUrl = new URL(req.url || "/", "http://127.0.0.1");
  req.query = Object.fromEntries(requestUrl.searchParams.entries());

  const handler = routes[requestUrl.pathname];
  if (handler) {
    try {
      await handler(req, res);
    } catch (error) {
      if (!res.headersSent) {
        res.status(500).json({
          ok: false,
          error: "server_error",
          message: String(error?.message || "Unhandled server error")
        });
      } else {
        res.end();
      }
    }
    return;
  }

  serveStatic(req, res, requestUrl.pathname);
});

const port = Number(process.env.PORT || 3000);
server.listen(port, () => {
  console.log(`BYDFI AgentOS local server listening on http://127.0.0.1:${port}`);
});
