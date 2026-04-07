const crypto = require("node:crypto");
const os = require("node:os");

function createSecretCodec() {
  const safeStorage = resolveSafeStorage();
  const fallbackKey = crypto
    .createHash("sha256")
    .update(
      process.env.THOHAGO_DESKTOP_FALLBACK_KEY ||
        `${os.hostname()}:${os.userInfo().username}:thohago-desktop`
    )
    .digest();

  return {
    encrypt(plainText) {
      if (!plainText) {
        return null;
      }

      if (safeStorage?.isEncryptionAvailable?.()) {
        return JSON.stringify({
          scheme: "safeStorage",
          payload: safeStorage.encryptString(plainText).toString("base64"),
        });
      }

      const iv = crypto.randomBytes(12);
      const cipher = crypto.createCipheriv("aes-256-gcm", fallbackKey, iv);
      const encrypted = Buffer.concat([
        cipher.update(plainText, "utf8"),
        cipher.final(),
      ]);
      const tag = cipher.getAuthTag();

      return JSON.stringify({
        scheme: "fallback-aes-gcm-v1",
        iv: iv.toString("base64"),
        tag: tag.toString("base64"),
        payload: encrypted.toString("base64"),
      });
    },

    decrypt(serialized) {
      if (!serialized) {
        return null;
      }

      const parsed = JSON.parse(serialized);
      if (parsed.scheme === "safeStorage") {
        if (!safeStorage?.isEncryptionAvailable?.()) {
          throw new Error("safeStorage is unavailable for stored secret");
        }
        return safeStorage.decryptString(Buffer.from(parsed.payload, "base64"));
      }

      if (parsed.scheme === "fallback-aes-gcm-v1") {
        const decipher = crypto.createDecipheriv(
          "aes-256-gcm",
          fallbackKey,
          Buffer.from(parsed.iv, "base64")
        );
        decipher.setAuthTag(Buffer.from(parsed.tag, "base64"));
        return Buffer.concat([
          decipher.update(Buffer.from(parsed.payload, "base64")),
          decipher.final(),
        ]).toString("utf8");
      }

      throw new Error(`unknown secret scheme: ${parsed.scheme}`);
    },
  };
}

function resolveSafeStorage() {
  try {
    const { safeStorage } = require("electron/main");
    return safeStorage;
  } catch (_error) {
    // Fallback below.
  }

  try {
    const { safeStorage } = require("electron");
    return safeStorage;
  } catch (_error) {
    return null;
  }
}

module.exports = {
  createSecretCodec,
};
