const { spawn } = require("node:child_process");
const readline = require("node:readline");
const { createRequest } = require("./json-rpc");

class SidecarProcessManager {
  constructor(options) {
    this.command = options.command;
    this.args = options.args ?? [];
    this.cwd = options.cwd;
    this.env = options.env ?? process.env;
    this.logger = options.logger ?? (() => {});
    this.process = null;
    this.pending = new Map();
    this.notificationHandlers = new Set();
    this.restartTimer = null;
    this.restartAttempts = 0;
    this.stopping = false;
    this.status = {
      state: "stopped",
      pid: null,
      lastError: null,
      restartAttempts: 0,
      startedAt: null,
      connectedAt: null,
    };
  }

  onNotification(handler) {
    this.notificationHandlers.add(handler);
    return () => this.notificationHandlers.delete(handler);
  }

  getStatus() {
    return { ...this.status };
  }

  async start() {
    if (this.process) {
      return this.getStatus();
    }

    this.stopping = false;
    this.status = {
      ...this.status,
      state: "starting",
      lastError: null,
      startedAt: new Date().toISOString(),
    };
    this.logger(`starting sidecar: ${this.command} ${this.args.join(" ")}`);

    const child = spawn(this.command, this.args, {
      cwd: this.cwd,
      env: {
        ...this.env,
        PYTHONIOENCODING: this.env.PYTHONIOENCODING || "utf-8",
        PYTHONUTF8: this.env.PYTHONUTF8 || "1",
      },
      stdio: ["pipe", "pipe", "pipe"],
      windowsHide: true,
    });

    this.process = child;
    this.status.pid = child.pid ?? null;

    const stdout = readline.createInterface({ input: child.stdout });
    stdout.on("line", (line) => this.handleStdout(line));

    child.stderr.on("data", (chunk) => {
      this.logger(`sidecar stderr: ${String(chunk).trim()}`);
    });

    child.on("exit", (code, signal) => {
      this.logger(`sidecar exit: code=${code} signal=${signal}`);
      this.process = null;
      this.status = {
        ...this.status,
        state: this.stopping ? "stopped" : "error",
        pid: null,
        lastError: this.stopping
          ? null
          : `sidecar exited unexpectedly (code=${code}, signal=${signal})`,
      };
      this.rejectAllPending(
        new Error(this.status.lastError ?? "sidecar stopped before response")
      );
      if (!this.stopping) {
        this.scheduleRestart();
      }
    });

    child.on("error", (error) => {
      this.logger(`sidecar spawn error: ${error.message}`);
      this.status = {
        ...this.status,
        state: "error",
        lastError: error.message,
      };
    });

    await this.call("system.ping", {}, 5000);
    this.restartAttempts = 0;
    this.status = {
      ...this.status,
      state: "connected",
      restartAttempts: 0,
      connectedAt: new Date().toISOString(),
    };
    return this.getStatus();
  }

  async stop() {
    if (!this.process) {
      this.status = {
        ...this.status,
        state: "stopped",
        pid: null,
      };
      return;
    }

    this.stopping = true;
    clearTimeout(this.restartTimer);
    this.restartTimer = null;

    try {
      await this.call("system.shutdown", {}, 3000);
    } catch (error) {
      this.logger(`sidecar shutdown request failed: ${error.message}`);
    }

    const child = this.process;
    await new Promise((resolve) => {
      const timeout = setTimeout(() => {
        if (this.process === child && !child.killed) {
          child.kill();
        }
      }, 3000);

      child.once("exit", () => {
        clearTimeout(timeout);
        resolve();
      });
    });
  }

  async call(method, params = {}, timeoutMs = 5000) {
    if (!this.process) {
      throw new Error("sidecar process is not running");
    }

    const request = createRequest(method, params);
    const payload = JSON.stringify(request) + "\n";

    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.pending.delete(request.id);
        reject(new Error(`sidecar call timed out: ${method}`));
      }, timeoutMs);

      this.pending.set(request.id, {
        resolve: (result) => {
          clearTimeout(timeout);
          resolve(result);
        },
        reject: (error) => {
          clearTimeout(timeout);
          reject(error);
        },
      });

      this.process.stdin.write(payload, (error) => {
        if (error) {
          clearTimeout(timeout);
          this.pending.delete(request.id);
          reject(error);
        }
      });
    });
  }

  handleStdout(line) {
    if (!line.trim()) {
      return;
    }

    let message;
    try {
      message = JSON.parse(line);
    } catch (error) {
      this.logger(`sidecar stdout parse error: ${error.message} :: ${line}`);
      return;
    }

    if (message.id && this.pending.has(message.id)) {
      const pending = this.pending.get(message.id);
      this.pending.delete(message.id);
      if (message.error) {
        pending.reject(
          new Error(message.error.message ?? "sidecar returned an error")
        );
      } else {
        pending.resolve(message.result);
      }
      return;
    }

    if (message.method) {
      for (const handler of this.notificationHandlers) {
        handler(message.method, message.params ?? {});
      }
    }
  }

  rejectAllPending(error) {
    for (const pending of this.pending.values()) {
      pending.reject(error);
    }
    this.pending.clear();
  }

  scheduleRestart() {
    clearTimeout(this.restartTimer);
    this.restartAttempts += 1;
    const delay = Math.min(30000, 1000 * 2 ** (this.restartAttempts - 1));
    this.status = {
      ...this.status,
      restartAttempts: this.restartAttempts,
    };
    this.restartTimer = setTimeout(() => {
      this.start().catch((error) => {
        this.logger(`sidecar restart failed: ${error.message}`);
      });
    }, delay);
  }
}

module.exports = {
  SidecarProcessManager,
};
