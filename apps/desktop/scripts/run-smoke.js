const { spawn, spawnSync } = require("node:child_process");
const net = require("node:net");
const path = require("node:path");

const rootDir = path.resolve(__dirname, "..");
const pnpmCommand = process.platform === "win32" ? "pnpm.cmd" : "pnpm";
const nodeCommand = process.execPath;

async function waitForPort(port, timeoutMs = 20000) {
  const deadline = Date.now() + timeoutMs;

  while (Date.now() < deadline) {
    const connected = await new Promise((resolve) => {
      const socket = net.connect({ host: "127.0.0.1", port }, () => {
        socket.end();
        resolve(true);
      });
      socket.once("error", () => {
        resolve(false);
      });
    });

    if (connected) {
      return;
    }

    await new Promise((resolve) => setTimeout(resolve, 250));
  }

  throw new Error(`timed out waiting for port ${port}`);
}

async function main() {
  const vite = spawn(pnpmCommand, ["dev:renderer"], {
    cwd: rootDir,
    stdio: "inherit",
    env: process.env,
    shell: process.platform === "win32",
  });

  const shutdownVite = () => {
    if (vite.exitCode !== null) {
      return;
    }

    if (process.platform === "win32") {
      spawnSync("taskkill", ["/PID", String(vite.pid), "/T", "/F"], {
        stdio: "ignore",
      });
      return;
    }

    vite.kill();
  };

  try {
    await waitForPort(5173, 20000);

    const env = {
      ...process.env,
      VITE_DEV_SERVER_URL: "http://127.0.0.1:5173",
      THOHAGO_DESKTOP_SMOKE_MODE: process.env.THOHAGO_DESKTOP_SMOKE_MODE || "1",
      THOHAGO_DESKTOP_DATA_DIR:
        process.env.THOHAGO_DESKTOP_DATA_DIR || ".thohago-desktop/smoke",
      THOHAGO_DESKTOP_SMOKE_OUTPUT:
        process.env.THOHAGO_DESKTOP_SMOKE_OUTPUT ||
        ".thohago-desktop/smoke-report.json",
    };

    const electron = spawn(nodeCommand, ["scripts/run-electron.js", "."], {
      cwd: rootDir,
      stdio: "inherit",
      env,
    });

    const exitCode = await new Promise((resolve) => {
      electron.once("exit", (code) => resolve(code ?? 0));
    });

    shutdownVite();
    process.exit(exitCode);
  } catch (error) {
    shutdownVite();
    console.error(error);
    process.exit(1);
  }
}

main();
