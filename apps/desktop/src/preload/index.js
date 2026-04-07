const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("thohago", {
  app: {
    getBootstrap: () => ipcRenderer.invoke("app:bootstrap"),
    reportSnapshot: (snapshot) =>
      ipcRenderer.invoke("app:report-snapshot", snapshot),
    runPhase2SmokeScenario: () => ipcRenderer.invoke("app:run-phase2-smoke-scenario"),
    runPhase3SmokeScenario: () => ipcRenderer.invoke("app:run-phase3-smoke-scenario"),
  },
  onboarding: {
    checkDependencies: () => ipcRenderer.invoke("onboarding:check-dependencies"),
    complete: (payload) => ipcRenderer.invoke("onboarding:complete", payload),
    selectProjectFolder: () =>
      ipcRenderer.invoke("onboarding:select-project-folder"),
  },
  sidecar: {
    getStatus: () => ipcRenderer.invoke("sidecar:status"),
    ping: () => ipcRenderer.invoke("sidecar:ping"),
    getSystemStatus: () => ipcRenderer.invoke("sidecar:system-status"),
  },
  settings: {
    listInspectable: () => ipcRenderer.invoke("settings:list"),
  },
  projects: {
    list: () => ipcRenderer.invoke("project:list"),
    create: (payload) => ipcRenderer.invoke("project:create", payload),
    get: (projectId) => ipcRenderer.invoke("project:get", projectId),
    selectMediaFiles: () => ipcRenderer.invoke("project:select-media-files"),
    importMedia: (payload) => ipcRenderer.invoke("project:import-media", payload),
    setHeroMedia: (payload) => ipcRenderer.invoke("project:set-hero-media", payload),
    updateMediaOrder: (payload) =>
      ipcRenderer.invoke("project:update-media-order", payload),
    buildPreflight: (projectId) =>
      ipcRenderer.invoke("project:build-preflight", projectId),
    getGenerationDefaults: (projectId) =>
      ipcRenderer.invoke("project:get-generation-defaults", projectId),
    saveGenerationProfile: (payload) =>
      ipcRenderer.invoke("project:save-generation-profile", payload),
  },
  interview: {
    get: (projectId) => ipcRenderer.invoke("interview:get", projectId),
    start: (projectId) => ipcRenderer.invoke("interview:start", projectId),
    submitAnswer: (payload) => ipcRenderer.invoke("interview:submit-answer", payload),
  },
  content: {
    generateAll: (projectId) => ipcRenderer.invoke("content:generate-all", projectId),
    getSpec: (projectId, contentType) =>
      ipcRenderer.invoke("content:get-spec", { projectId, contentType }),
    getPreviewHtml: (projectId, contentType) =>
      ipcRenderer.invoke("content:get-preview-html", { projectId, contentType }),
    regenerate: (payload) => ipcRenderer.invoke("content:regenerate", payload),
    getRuns: (projectId, contentType) =>
      ipcRenderer.invoke("content:get-runs", { projectId, contentType }),
  },
  publish: {
    run: (payload) => ipcRenderer.invoke("publish:run", payload),
    getRuns: (projectId) => ipcRenderer.invoke("publish:get-runs", projectId),
    getSummary: (projectId) => ipcRenderer.invoke("publish:get-summary", projectId),
    runRecommended: (projectId) => ipcRenderer.invoke("publish:run-recommended", projectId),
    getCredentialStatus: () => ipcRenderer.invoke("publish:get-credential-status"),
    saveCredentials: (payload) => ipcRenderer.invoke("publish:save-credentials", payload),
    validateProvider: (provider) => ipcRenderer.invoke("publish:validate-provider", provider),
  },
});
