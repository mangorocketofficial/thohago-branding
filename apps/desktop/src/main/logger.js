const fs = require("node:fs");
const path = require("node:path");

function createFileLogger(logPath) {
  fs.mkdirSync(path.dirname(logPath), { recursive: true });

  return (message) => {
    const line = `[${new Date().toISOString()}] ${message}\n`;
    fs.appendFileSync(logPath, line, "utf8");
  };
}

module.exports = {
  createFileLogger,
};
