const { randomUUID } = require("node:crypto");

function createRequest(method, params) {
  return {
    jsonrpc: "2.0",
    id: randomUUID(),
    method,
    params: params ?? {},
  };
}

module.exports = {
  createRequest,
};
