const fs = require("node:fs");

class SettingsStore {
  constructor({ database, codec }) {
    this.database = database;
    this.codec = codec;
  }

  getBootstrap() {
    const onboardingCompleted =
      this.getPlain("onboarding_completed") === "1";
    const projectRootPath = this.getPlain("project_root_path");
    const dependencyCheck = this.getJson("last_dependency_check");

    return {
      onboardingCompleted,
      projectRootPath,
      dependencyCheck,
      apiKeys: {
        gemini: Boolean(this.getSecret("gemini_api_key")),
        anthropic: Boolean(this.getSecret("anthropic_api_key")),
        openai: Boolean(this.getSecret("openai_api_key")),
      },
      publishCredentials: this.getPublishCredentialStatus(),
    };
  }

  completeOnboarding(payload) {
    const projectRootPath = payload.projectRootPath?.trim();
    if (!projectRootPath) {
      throw new Error("project root path is required");
    }

    fs.mkdirSync(projectRootPath, { recursive: true });
    this.setPlain("project_root_path", projectRootPath);
    this.setSecret("gemini_api_key", payload.apiKeys?.gemini ?? "");
    this.setSecret("anthropic_api_key", payload.apiKeys?.anthropic ?? "");
    this.setSecret("openai_api_key", payload.apiKeys?.openai ?? "");
    this.setJson("last_dependency_check", payload.dependencyCheck ?? null);
    this.setPlain("onboarding_completed", "1");
  }

  resetOnboarding() {
    this.setPlain("onboarding_completed", "0");
  }

  setPlain(key, value) {
    this.upsert(key, value ?? "", 0);
  }

  getPlain(key) {
    const row = this.database.get(
      "SELECT value FROM settings WHERE key = ?",
      [key]
    );
    return row ? row.value : null;
  }

  setJson(key, value) {
    if (value == null) {
      this.delete(key);
      return;
    }
    this.upsert(key, JSON.stringify(value), 0);
  }

  getJson(key) {
    const value = this.getPlain(key);
    return value ? JSON.parse(value) : null;
  }

  setSecret(key, plainText) {
    if (!plainText || !plainText.trim()) {
      this.delete(key);
      return;
    }

    this.upsert(key, this.codec.encrypt(plainText.trim()), 1);
  }

  getSecret(key) {
    const row = this.database.get(
      "SELECT value, is_encrypted FROM settings WHERE key = ?",
      [key]
    );
    if (!row) {
      return null;
    }
    return row.is_encrypted ? this.codec.decrypt(row.value) : row.value;
  }

  listInspectableSettings() {
    return this.database.all(
      "SELECT key, is_encrypted, updated_at FROM settings ORDER BY key"
    );
  }

  savePublishCredentials(payload) {
    this.setSecret("graph_meta_access_token", payload.graphMetaAccessToken ?? "");
    this.setPlain(
      "instagram_business_account_id",
      (payload.instagramBusinessAccountId || "").trim()
    );
    this.setPlain("facebook_page_id", (payload.facebookPageId || "").trim());
    this.setPlain(
      "instagram_graph_version",
      (payload.instagramGraphVersion || "v23.0").trim()
    );
    this.setSecret("threads_access_token", payload.threadsAccessToken ?? "");
    this.setPlain("threads_user_id", (payload.threadsUserId || "").trim());
    this.setPlain("naver_live_note", (payload.naverLiveNote || "").trim());
  }

  getPublishCredentials() {
    return {
      graphMetaAccessToken: this.getSecret("graph_meta_access_token"),
      instagramBusinessAccountId: this.getPlain("instagram_business_account_id"),
      facebookPageId: this.getPlain("facebook_page_id"),
      instagramGraphVersion: this.getPlain("instagram_graph_version") || "v23.0",
      threadsAccessToken: this.getSecret("threads_access_token"),
      threadsUserId: this.getPlain("threads_user_id"),
      naverLiveNote: this.getPlain("naver_live_note"),
    };
  }

  getPublishCredentialStatus() {
    return {
      instagram: {
        accessTokenPresent: Boolean(this.getSecret("graph_meta_access_token")),
        instagramBusinessAccountId:
          this.getPlain("instagram_business_account_id") || "",
        facebookPageId: this.getPlain("facebook_page_id") || "",
        instagramGraphVersion: this.getPlain("instagram_graph_version") || "v23.0",
      },
      threads: {
        accessTokenPresent: Boolean(this.getSecret("threads_access_token")),
        threadsUserId: this.getPlain("threads_user_id") || "",
        facebookPageId: this.getPlain("facebook_page_id") || "",
      },
      naver: {
        liveNotePresent: Boolean(this.getPlain("naver_live_note")),
        naverLiveNote: this.getPlain("naver_live_note") || "",
      },
      validation: {
        instagram: this.getJson("publish_validation_instagram"),
        threads: this.getJson("publish_validation_threads"),
        naver: this.getJson("publish_validation_naver"),
      },
    };
  }

  setPublishValidationResult(provider, result) {
    this.setJson(`publish_validation_${provider}`, result);
  }

  upsert(key, value, isEncrypted) {
    this.database.run(
      `
      INSERT INTO settings (key, value, is_encrypted, updated_at)
      VALUES (?, ?, ?, CURRENT_TIMESTAMP)
      ON CONFLICT(key) DO UPDATE SET
        value = excluded.value,
        is_encrypted = excluded.is_encrypted,
        updated_at = CURRENT_TIMESTAMP
      `,
      [key, value, isEncrypted]
    );
  }

  delete(key) {
    this.database.run("DELETE FROM settings WHERE key = ?", [key]);
  }
}

module.exports = {
  SettingsStore,
};
