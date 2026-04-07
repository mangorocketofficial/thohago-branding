const fs = require("node:fs");
const path = require("node:path");
const { spawnSync } = require("node:child_process");
const { SidecarProcessManager } = require("@thohago/python-sidecar");
const { createDatabase } = require("./database");
const { createFileLogger } = require("./logger");
const { ContentGenerationService } = require("./content-generation");
const { PublishService } = require("./publish-service");
const { ProjectService, InterviewService } = require("./projects");
const { createSecretCodec } = require("./security");
const { SettingsStore } = require("./settings");

const electronMain = loadElectronMain();
const { app, BrowserWindow, dialog, ipcMain } = electronMain;

let mainWindow = null;
let database = null;
let settingsStore = null;
let sidecarManager = null;
let projectService = null;
let interviewService = null;
let contentGenerationService = null;
let publishService = null;
let appState = null;
let smokeReport = null;
let isQuittingGracefully = false;

const APP_TITLE = "Thohago Desktop";
const logToConsole = (...args) => {
  console.log("[desktop-main]", ...args);
};

function loadElectronMain() {
  try {
    const resolved = require("electron/main");
    if (resolved?.app) {
      return resolved;
    }
  } catch (_error) {
    // Fallback below.
  }

  const resolved = require("electron");
  if (resolved?.app) {
    return resolved;
  }

  throw new Error("Electron main-process modules are unavailable");
}

function getRepoRoot() {
  return path.resolve(__dirname, "../../../../");
}

function resolveDesktopDataDir() {
  const override = process.env.THOHAGO_DESKTOP_DATA_DIR;
  if (override) {
    return path.resolve(process.cwd(), override);
  }
  return path.join(app.getPath("userData"), "foundation");
}

function mergePythonPath(repoRoot) {
  const existing = process.env.PYTHONPATH
    ? process.env.PYTHONPATH.split(path.delimiter)
    : [];
  return [repoRoot, path.join(repoRoot, "src"), ...existing]
    .filter(Boolean)
    .join(path.delimiter);
}

function runDependencyCommand(command, args) {
  const result = spawnSync(command, args, {
    cwd: appState.repoRoot,
    encoding: "utf8",
    windowsHide: true,
  });

  return {
    command: [command, ...args].join(" "),
    available: result.status === 0,
    status: result.status,
    stdout: (result.stdout || "").trim(),
    stderr: (result.stderr || "").trim(),
    error: result.error ? result.error.message : null,
  };
}

async function createApplicationState() {
  const repoRoot = getRepoRoot();
  const dataDir = resolveDesktopDataDir();
  const logsDir = path.join(dataDir, "logs");
  const dbPath = path.join(dataDir, "thohago-desktop.sqlite");
  const mainLog = createFileLogger(path.join(logsDir, "main.log"));
  const sidecarLog = createFileLogger(path.join(logsDir, "sidecar.log"));

  const db = await createDatabase({
    dbPath,
    migrationsDir: path.join(repoRoot, "migrations", "desktop"),
    logger: mainLog,
  });

  const settings = new SettingsStore({
    database: db,
    codec: createSecretCodec(),
  });

  const sidecar = new SidecarProcessManager({
    command: process.env.THOHAGO_DESKTOP_PYTHON || "python",
    args: ["-u", "-m", "sidecar.server", "--project-root", repoRoot],
    cwd: repoRoot,
    env: {
      ...process.env,
      PYTHONPATH: mergePythonPath(repoRoot),
    },
    logger: sidecarLog,
  });

  try {
    await sidecar.start();
  } catch (error) {
    mainLog(`sidecar start failed: ${error.message}`);
  }

  mainLog(`repoRoot=${repoRoot}`);
  mainLog(`dataDir=${dataDir}`);
  logToConsole(`repoRoot=${repoRoot}`);
  logToConsole(`dataDir=${dataDir}`);

  return {
    repoRoot,
    dataDir,
    logsDir,
    dbPath,
    mainLog,
    db,
    settings,
    sidecar,
  };
}

async function buildBootstrapPayload() {
  const settingsSnapshot = settingsStore.getBootstrap();
  return {
    appTitle: APP_TITLE,
    version: app.getVersion(),
    smokeMode: process.env.THOHAGO_DESKTOP_SMOKE_MODE === "1",
    smokeFlow: process.env.THOHAGO_DESKTOP_SMOKE_FLOW || "phase1",
    paths: {
      dataDir: appState.dataDir,
      dbPath: appState.dbPath,
      logsDir: appState.logsDir,
    },
    settings: settingsSnapshot,
    sidecar: sidecarManager.getStatus(),
  };
}

async function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1360,
    height: 920,
    minWidth: 1120,
    minHeight: 760,
    title: APP_TITLE,
    webPreferences: {
      preload: path.join(__dirname, "../preload/index.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  mainWindow.webContents.on("did-finish-load", () => {
    logToConsole("renderer did-finish-load");
  });
  mainWindow.webContents.on(
    "did-fail-load",
    (_event, errorCode, errorDescription, validatedURL) => {
      logToConsole(
        `renderer did-fail-load code=${errorCode} description=${errorDescription} url=${validatedURL}`
      );
    }
  );
  mainWindow.webContents.on(
    "console-message",
    (_event, level, message, line, sourceId) => {
      logToConsole(
        `renderer console level=${level} message=${message} source=${sourceId}:${line}`
      );
    }
  );

  const devServerUrl = process.env.VITE_DEV_SERVER_URL;
  if (devServerUrl) {
    logToConsole(`loading renderer from ${devServerUrl}`);
    await mainWindow.loadURL(devServerUrl);
  } else {
    const fallbackHtml = `
      <html>
        <body style="font-family: Segoe UI, sans-serif; background:#faf3e8; color:#2f241f; padding:40px;">
          <h1>${APP_TITLE}</h1>
          <p>Renderer 개발 서버가 실행 중이 아닙니다.</p>
          <p>저장소 루트에서 <code>pnpm desktop:dev</code>를 실행하세요.</p>
        </body>
      </html>
    `;
    await mainWindow.loadURL(`data:text/html;charset=UTF-8,${encodeURIComponent(fallbackHtml)}`);
  }

}

function writeSmokeReport() {
  if (!smokeReport?.outputPath) {
    return;
  }

  fs.mkdirSync(path.dirname(smokeReport.outputPath), { recursive: true });
  fs.writeFileSync(
    smokeReport.outputPath,
    JSON.stringify(smokeReport, null, 2),
    "utf8"
  );
  logToConsole(`smoke report written to ${smokeReport.outputPath}`);
}

function navigateToHash(hashPath) {
  if (!mainWindow || mainWindow.isDestroyed()) {
    return;
  }

  const escaped = JSON.stringify(`#${hashPath}`);
  mainWindow.webContents.executeJavaScript(`window.location.hash = ${escaped};`);
}

function getPhase2FixtureFiles() {
  const fixtureRoot = path.join(
    appState.repoRoot,
    "client",
    "sisun8082",
    "2026_03_27",
    "images"
  );
  return [
    path.join(fixtureRoot, "KakaoTalk_20260327_121540482.jpg"),
    path.join(fixtureRoot, "KakaoTalk_20260327_121540482_01.jpg"),
    path.join(fixtureRoot, "KakaoTalk_20260327_121540482_02.jpg"),
  ].filter((filePath) => fs.existsSync(filePath));
}

async function runPhase2SmokeScenario() {
  const project = projectService.createProject({
    name: "phase2-smoke-project",
    shopDisplayName: "Smoke Beauty Studio",
    summary: "Phase 2 local verification project",
  });
  const fixtureFiles = getPhase2FixtureFiles();
  if (fixtureFiles.length === 0) {
    throw new Error("phase2 smoke fixtures are missing");
  }

  let current = projectService.importMedia(project.id, fixtureFiles);
  current = projectService.setRepresentativeMedia(current.id, current.mediaAssets[0].id);
  current = await projectService.buildPreflight(current.id);
  let session = await interviewService.startInterview(current.id);
  session = await interviewService.submitAnswer(
    current.id,
    "처음 방문한 손님이 들어오면 따뜻하고 편안한 분위기부터 느끼셨으면 좋겠어요."
  );
  session = await interviewService.submitAnswer(
    current.id,
    "상담부터 샴푸, 시술, 마무리까지 급하지 않게 차분하게 진행되는 점을 강조하고 싶어요."
  );
  session = await interviewService.submitAnswer(
    current.id,
    "결과만이 아니라 고객이 쉬어가는 경험까지 챙기는 곳이라는 말을 꼭 남기고 싶습니다."
  );

  const updatedProject = projectService.getProject(current.id);
  return {
    projectId: updatedProject.id,
    sessionId: session.id,
    projectFolderPath: updatedProject.projectFolderPath,
    mediaCount: updatedProject.mediaAssets.length,
    interviewStatus: session.status,
  };
}

async function runPhase3SmokeScenario() {
  const phase2 = await runPhase2SmokeScenario();
  const defaults = projectService.getGenerationDefaults(phase2.projectId);
  const project = projectService.saveGenerationProfile(phase2.projectId, {
    ...defaults,
    industry: "salon",
    tone: "premium",
    contentLength: "standard",
    emphasisPoint: "calm consultation and premium scalp-care experience",
    mustIncludeKeywords: ["premium scalp care", "calm consultation"],
    excludedPhrases: ["cheap", "must visit"],
  });

  return {
    ...phase2,
    projectStatus: project.status,
    generationProfile: project.generationProfile,
  };
}

async function runPhase4SmokeScenario() {
  const phase3 = await runPhase3SmokeScenario();
  const project = await contentGenerationService.generateAll(phase3.projectId);
  return {
    ...phase3,
    projectStatus: project.status,
    generatedContentCount: project.generatedContentCount,
    contentTypes: project.contentSpecs.map((entry) => entry.contentType),
  };
}

async function runPhase6SmokeScenario() {
  const phase4 = await runPhase4SmokeScenario();
  await contentGenerationService.regenerateContent(
    phase4.projectId,
    "blog",
    "premium"
  );
  await contentGenerationService.regenerateContent(
    phase4.projectId,
    "carousel",
    "cta_boost"
  );
  await contentGenerationService.regenerateContent(
    phase4.projectId,
    "video",
    "length_shorter"
  );
  await contentGenerationService.regenerateContent(
    phase4.projectId,
    "thread",
    "tone_shift"
  );

  return {
    ...phase4,
    regenerationModes: {
      blog: "premium",
      carousel: "cta_boost",
      video: "length_shorter",
      thread: "tone_shift",
    },
  };
}

async function runPhase7SmokeScenario() {
  const phase6 = await runPhase6SmokeScenario();
  await publishService.publishContent(phase6.projectId, "blog");
  await publishService.publishContent(phase6.projectId, "carousel");
  await publishService.publishContent(phase6.projectId, "video");
  await publishService.publishContent(phase6.projectId, "thread");
  const project = projectService.getProject(phase6.projectId);
  return {
    ...phase6,
    projectStatus: project.status,
    publishedContentCount: project.publishedContentCount,
  };
}

async function runPhase8SmokeScenario() {
  const phase7 = await runPhase7SmokeScenario();
  publishService.saveCredentials({
    graphMetaAccessToken: "phase8-instagram-token",
    instagramBusinessAccountId: "17841400000000000",
    facebookPageId: "",
    instagramGraphVersion: "v23.0",
    threadsAccessToken: "phase8-threads-token",
    threadsUserId: "1234567890",
    naverLiveNote: "Manual Naver live publishing setup pending",
  });
  const instagram = await publishService.validateProvider("instagram");
  const threads = await publishService.validateProvider("threads");
  const naver = await publishService.validateProvider("naver");
  return {
    ...phase7,
    credentialStatus: publishService.getCredentialStatus(),
    validationSequence: [
      instagram.validation.instagram,
      threads.validation.threads,
      naver.validation.naver,
    ],
  };
}

async function runPhase9SmokeScenario() {
  const phase4 = await runPhase4SmokeScenario();
  publishService.saveCredentials({
    graphMetaAccessToken: "phase9-instagram-token",
    instagramBusinessAccountId: "17841400000000000",
    facebookPageId: "",
    instagramGraphVersion: "v23.0",
    threadsAccessToken: "phase9-threads-token",
    threadsUserId: "1234567890",
    naverLiveNote: "Manual Naver live publishing setup pending",
  });
  await publishService.publishContent(phase4.projectId, "blog", "live");
  await publishService.publishContent(phase4.projectId, "carousel", "live");
  await publishService.publishContent(phase4.projectId, "video", "live");
  await publishService.publishContent(phase4.projectId, "thread", "live");
  return {
    ...phase4,
    credentialStatus: publishService.getCredentialStatus(),
    livePublishMap: publishService.getLatestPublishMap(phase4.projectId),
  };
}

async function runPhase10SmokeScenario() {
  const phase4 = await runPhase4SmokeScenario();
  publishService.saveCredentials({
    graphMetaAccessToken: "phase10-instagram-token",
    instagramBusinessAccountId: "17841400000000000",
    facebookPageId: "",
    instagramGraphVersion: "v23.0",
    threadsAccessToken: "phase10-threads-token",
    threadsUserId: "1234567890",
    naverLiveNote: "Manual Naver live publishing setup pending",
  });
  await publishService.validateProvider("instagram");
  await publishService.validateProvider("threads");
  await publishService.validateProvider("naver");
  const recommended = await publishService.runRecommendedPublish(phase4.projectId);
  return {
    ...phase4,
    credentialStatus: publishService.getCredentialStatus(),
    recommendedAttemptedContentTypes: recommended.attemptedContentTypes,
    publishSummary: recommended.summary,
  };
}

function registerIpcHandlers() {
  ipcMain.handle("app:bootstrap", async () => buildBootstrapPayload());

  ipcMain.handle("app:report-snapshot", async (_event, snapshot) => {
    if (!smokeReport) {
      return { recorded: false };
    }

    smokeReport.snapshots.push({
      ...snapshot,
      recordedAt: new Date().toISOString(),
    });

    const smokeFlow = process.env.THOHAGO_DESKTOP_SMOKE_FLOW || "phase1";
    if ((smokeFlow === "phase5" || smokeFlow === "phase5-restart") && snapshot.contentType) {
      const seen = new Set(smokeReport.phase5SeenContentTypes || []);
      seen.add(snapshot.contentType);
      smokeReport.phase5SeenContentTypes = Array.from(seen);
    }
    if ((smokeFlow === "phase6" || smokeFlow === "phase6-restart") && snapshot.contentType) {
      const seen = new Set(smokeReport.phase6SeenContentTypes || []);
      seen.add(snapshot.contentType);
      smokeReport.phase6SeenContentTypes = Array.from(seen);
    }
    if ((smokeFlow === "phase6" || smokeFlow === "phase6-restart") && snapshot.regenerationMode) {
      smokeReport.phase6LastMode = snapshot.regenerationMode;
    }
    if ((smokeFlow === "phase7" || smokeFlow === "phase7-restart") && snapshot.publishedContentCount != null) {
      smokeReport.phase7PublishedContentCount = snapshot.publishedContentCount;
    }
    if ((smokeFlow === "phase8" || smokeFlow === "phase8-restart") && snapshot.route?.endsWith("/publish")) {
      smokeReport.phase8CredentialSnapshot = {
        instagramCredentialPresent: snapshot.instagramCredentialPresent,
        threadsCredentialPresent: snapshot.threadsCredentialPresent,
        instagramValidation: snapshot.instagramValidation,
        threadsValidation: snapshot.threadsValidation,
        naverValidation: snapshot.naverValidation,
      };
    }
    if ((smokeFlow === "phase9" || smokeFlow === "phase9-restart") && snapshot.route?.endsWith("/publish")) {
      smokeReport.phase9PublishSnapshot = {
        publishRunCount: snapshot.publishRunCount,
        latestPublishStatuses: snapshot.latestPublishStatuses,
        latestPublishModes: snapshot.latestPublishModes,
      };
    }
    if ((smokeFlow === "phase10" || smokeFlow === "phase10-restart") && snapshot.route?.endsWith("/publish")) {
      smokeReport.phase10PublishSnapshot = {
        publishRunCount: snapshot.publishRunCount,
        latestPublishStatuses: snapshot.latestPublishStatuses,
        latestPublishModes: snapshot.latestPublishModes,
        publishSummaryCounts: snapshot.publishSummaryCounts,
      };
    }
    writeSmokeReport();
    if (
      smokeFlow === "phase4" &&
      snapshot.route === "/" &&
      snapshot.onboardingCompleted &&
      !smokeReport?.scenario &&
      !smokeReport?.phase4Started
    ) {
      if (smokeReport) {
        smokeReport.phase4Started = true;
        writeSmokeReport();
      }
      runPhase4SmokeScenario()
        .then((scenario) => {
          if (smokeReport) {
            smokeReport.scenario = scenario;
            writeSmokeReport();
          }
          navigateToHash(`/project/${scenario.projectId}/blog`);
          setTimeout(() => {
            navigateToHash(`/project/${scenario.projectId}/carousel`);
          }, 250);
          setTimeout(() => {
            navigateToHash(`/project/${scenario.projectId}/video`);
          }, 500);
          setTimeout(() => {
            navigateToHash(`/project/${scenario.projectId}/thread`);
          }, 750);
          setTimeout(() => {
            navigateToHash(`/project/${scenario.projectId}`);
          }, 1050);
        })
        .catch((error) => {
          logToConsole(`phase4 smoke scenario failed: ${error.message}`);
        });
    }

    if (
      smokeFlow === "phase4-restart" &&
      snapshot.route === "/" &&
      snapshot.onboardingCompleted &&
      !smokeReport?.phase4RestartStarted
    ) {
      if (smokeReport) {
        smokeReport.phase4RestartStarted = true;
        writeSmokeReport();
      }
      const projects = projectService.listProjects();
      if (projects.length > 0) {
        navigateToHash(`/project/${projects[0].id}/blog`);
        setTimeout(() => {
          navigateToHash(`/project/${projects[0].id}`);
        }, 450);
      }
    }

    if (
      smokeFlow === "phase5" &&
      snapshot.route === "/" &&
      snapshot.onboardingCompleted &&
      !smokeReport?.scenario &&
      !smokeReport?.phase5Started
    ) {
      if (smokeReport) {
        smokeReport.phase5Started = true;
        writeSmokeReport();
      }
      runPhase4SmokeScenario()
        .then((scenario) => {
          if (smokeReport) {
            smokeReport.scenario = scenario;
            writeSmokeReport();
          }
          navigateToHash(`/project/${scenario.projectId}/blog`);
          setTimeout(() => {
            navigateToHash(`/project/${scenario.projectId}/carousel`);
          }, 400);
          setTimeout(() => {
            navigateToHash(`/project/${scenario.projectId}/video`);
          }, 850);
          setTimeout(() => {
            navigateToHash(`/project/${scenario.projectId}/thread`);
          }, 1300);
          setTimeout(() => {
            navigateToHash(`/project/${scenario.projectId}`);
          }, 1750);
        })
        .catch((error) => {
          logToConsole(`phase5 smoke scenario failed: ${error.message}`);
        });
    }

    if (
      smokeFlow === "phase5-restart" &&
      snapshot.route === "/" &&
      snapshot.onboardingCompleted &&
      !smokeReport?.phase5RestartStarted
    ) {
      if (smokeReport) {
        smokeReport.phase5RestartStarted = true;
        writeSmokeReport();
      }
      const projects = projectService.listProjects();
      if (projects.length > 0) {
        navigateToHash(`/project/${projects[0].id}/blog`);
        setTimeout(() => {
          navigateToHash(`/project/${projects[0].id}/carousel`);
        }, 400);
        setTimeout(() => {
          navigateToHash(`/project/${projects[0].id}/video`);
        }, 850);
        setTimeout(() => {
          navigateToHash(`/project/${projects[0].id}/thread`);
        }, 1300);
        setTimeout(() => {
          navigateToHash(`/project/${projects[0].id}`);
        }, 1750);
      }
    }

    if (
      smokeFlow === "phase6" &&
      snapshot.route === "/" &&
      snapshot.onboardingCompleted &&
      !smokeReport?.scenario &&
      !smokeReport?.phase6Started
    ) {
      if (smokeReport) {
        smokeReport.phase6Started = true;
        writeSmokeReport();
      }
      runPhase6SmokeScenario()
        .then((scenario) => {
          if (smokeReport) {
            smokeReport.scenario = scenario;
            writeSmokeReport();
          }
          navigateToHash(`/project/${scenario.projectId}/blog`);
          setTimeout(() => {
            navigateToHash(`/project/${scenario.projectId}/carousel`);
          }, 400);
          setTimeout(() => {
            navigateToHash(`/project/${scenario.projectId}/video`);
          }, 850);
          setTimeout(() => {
            navigateToHash(`/project/${scenario.projectId}/thread`);
          }, 1300);
          setTimeout(() => {
            navigateToHash(`/project/${scenario.projectId}`);
          }, 1750);
        })
        .catch((error) => {
          logToConsole(`phase6 smoke scenario failed: ${error.message}`);
        });
    }

    if (
      smokeFlow === "phase6-restart" &&
      snapshot.route === "/" &&
      snapshot.onboardingCompleted &&
      !smokeReport?.phase6RestartStarted
    ) {
      if (smokeReport) {
        smokeReport.phase6RestartStarted = true;
        writeSmokeReport();
      }
      const projects = projectService.listProjects();
      if (projects.length > 0) {
        navigateToHash(`/project/${projects[0].id}/blog`);
        setTimeout(() => {
          navigateToHash(`/project/${projects[0].id}/carousel`);
        }, 400);
        setTimeout(() => {
          navigateToHash(`/project/${projects[0].id}/video`);
        }, 850);
        setTimeout(() => {
          navigateToHash(`/project/${projects[0].id}/thread`);
        }, 1300);
        setTimeout(() => {
          navigateToHash(`/project/${projects[0].id}`);
        }, 1750);
      }
    }

    if (
      smokeFlow === "phase7" &&
      snapshot.route === "/" &&
      snapshot.onboardingCompleted &&
      !smokeReport?.scenario &&
      !smokeReport?.phase7Started
    ) {
      if (smokeReport) {
        smokeReport.phase7Started = true;
        writeSmokeReport();
      }
      runPhase7SmokeScenario()
        .then((scenario) => {
          if (smokeReport) {
            smokeReport.scenario = scenario;
            writeSmokeReport();
          }
          navigateToHash(`/project/${scenario.projectId}/publish`);
          setTimeout(() => {
            navigateToHash(`/project/${scenario.projectId}`);
          }, 900);
        })
        .catch((error) => {
          logToConsole(`phase7 smoke scenario failed: ${error.message}`);
        });
    }

    if (
      smokeFlow === "phase7-restart" &&
      snapshot.route === "/" &&
      snapshot.onboardingCompleted &&
      !smokeReport?.phase7RestartStarted
    ) {
      if (smokeReport) {
        smokeReport.phase7RestartStarted = true;
        writeSmokeReport();
      }
      const projects = projectService.listProjects();
      if (projects.length > 0) {
        navigateToHash(`/project/${projects[0].id}/publish`);
        setTimeout(() => {
          navigateToHash(`/project/${projects[0].id}`);
        }, 900);
      }
    }

    if (
      smokeFlow === "phase8" &&
      snapshot.route === "/" &&
      snapshot.onboardingCompleted &&
      !smokeReport?.scenario &&
      !smokeReport?.phase8Started
    ) {
      if (smokeReport) {
        smokeReport.phase8Started = true;
        writeSmokeReport();
      }
      runPhase8SmokeScenario()
        .then((scenario) => {
          if (smokeReport) {
            smokeReport.scenario = scenario;
            writeSmokeReport();
          }
          navigateToHash(`/project/${scenario.projectId}/publish`);
        })
        .catch((error) => {
          logToConsole(`phase8 smoke scenario failed: ${error.message}`);
        });
    }

    if (
      smokeFlow === "phase8-restart" &&
      snapshot.route === "/" &&
      snapshot.onboardingCompleted &&
      !smokeReport?.phase8RestartStarted
    ) {
      if (smokeReport) {
        smokeReport.phase8RestartStarted = true;
        writeSmokeReport();
      }
      const projects = projectService.listProjects();
      if (projects.length > 0) {
        navigateToHash(`/project/${projects[0].id}/publish`);
      }
    }

    if (
      smokeFlow === "phase9" &&
      snapshot.route === "/" &&
      snapshot.onboardingCompleted &&
      !smokeReport?.scenario &&
      !smokeReport?.phase9Started
    ) {
      if (smokeReport) {
        smokeReport.phase9Started = true;
        writeSmokeReport();
      }
      runPhase9SmokeScenario()
        .then((scenario) => {
          if (smokeReport) {
            smokeReport.scenario = scenario;
            writeSmokeReport();
          }
          navigateToHash(`/project/${scenario.projectId}/publish`);
        })
        .catch((error) => {
          logToConsole(`phase9 smoke scenario failed: ${error.message}`);
        });
    }

    if (
      smokeFlow === "phase9-restart" &&
      snapshot.route === "/" &&
      snapshot.onboardingCompleted &&
      !smokeReport?.phase9RestartStarted
    ) {
      if (smokeReport) {
        smokeReport.phase9RestartStarted = true;
        writeSmokeReport();
      }
      const projects = projectService.listProjects();
      if (projects.length > 0) {
        navigateToHash(`/project/${projects[0].id}/publish`);
      }
    }

    if (
      smokeFlow === "phase10" &&
      snapshot.route === "/" &&
      snapshot.onboardingCompleted &&
      !smokeReport?.scenario &&
      !smokeReport?.phase10Started
    ) {
      if (smokeReport) {
        smokeReport.phase10Started = true;
        writeSmokeReport();
      }
      runPhase10SmokeScenario()
        .then((scenario) => {
          if (smokeReport) {
            smokeReport.scenario = scenario;
            writeSmokeReport();
          }
          navigateToHash(`/project/${scenario.projectId}/publish`);
        })
        .catch((error) => {
          logToConsole(`phase10 smoke scenario failed: ${error.message}`);
        });
    }

    if (
      smokeFlow === "phase10-restart" &&
      snapshot.route === "/" &&
      snapshot.onboardingCompleted &&
      !smokeReport?.phase10RestartStarted
    ) {
      if (smokeReport) {
        smokeReport.phase10RestartStarted = true;
        writeSmokeReport();
      }
      const projects = projectService.listProjects();
      if (projects.length > 0) {
        navigateToHash(`/project/${projects[0].id}/publish`);
      }
    }

    if (
      smokeFlow === "phase1" &&
      snapshot.route === "/" &&
      snapshot.onboardingCompleted
    ) {
      setTimeout(() => {
        app.quit();
      }, 500);
    }

    if (
      smokeFlow === "phase2" &&
      smokeReport?.scenario?.projectId &&
      snapshot.route === `/project/${smokeReport.scenario.projectId}` &&
      snapshot.interviewStatus === "completed"
    ) {
      setTimeout(() => {
        app.quit();
      }, 500);
    }

    if (
      smokeFlow === "phase2-restart" &&
      typeof snapshot.route === "string" &&
      snapshot.route.startsWith("/project/") &&
      snapshot.interviewStatus === "completed"
    ) {
      setTimeout(() => {
        app.quit();
      }, 500);
    }

    if (
      smokeFlow === "phase3" &&
      smokeReport?.scenario?.projectId &&
      snapshot.route === `/project/${smokeReport.scenario.projectId}` &&
      snapshot.projectStatus === "ready_to_generate"
    ) {
      setTimeout(() => {
        app.quit();
      }, 500);
    }

    if (
      smokeFlow === "phase3-restart" &&
      typeof snapshot.route === "string" &&
      snapshot.route.startsWith("/project/") &&
      snapshot.projectStatus === "ready_to_generate"
    ) {
      setTimeout(() => {
        app.quit();
      }, 500);
    }

    if (
      smokeFlow === "phase4" &&
      smokeReport?.scenario?.projectId &&
      snapshot.route === `/project/${smokeReport.scenario.projectId}` &&
      snapshot.projectStatus === "content_generated" &&
      snapshot.generatedContentCount === 4
    ) {
      setTimeout(() => {
        app.quit();
      }, 500);
    }

    if (
      smokeFlow === "phase4-restart" &&
      typeof snapshot.route === "string" &&
      snapshot.route.startsWith("/project/") &&
      snapshot.projectStatus === "content_generated" &&
      snapshot.generatedContentCount === 4
    ) {
      setTimeout(() => {
        app.quit();
      }, 500);
    }

    if (
      smokeFlow === "phase5" &&
      typeof snapshot.route === "string" &&
      snapshot.route.startsWith("/project/") &&
      snapshot.projectStatus === "content_generated" &&
      snapshot.generatedContentCount === 4
    ) {
      const projectRouteHit = snapshot.route.split("/").length === 3;
      const seenCount = (smokeReport.phase5SeenContentTypes || []).length;
      if (projectRouteHit && seenCount >= 4) {
        setTimeout(() => {
          app.quit();
        }, 500);
      }
    }

    if (
      smokeFlow === "phase5-restart" &&
      typeof snapshot.route === "string" &&
      snapshot.route.startsWith("/project/") &&
      snapshot.projectStatus === "content_generated" &&
      snapshot.generatedContentCount === 4
    ) {
      const projectRouteHit = snapshot.route.split("/").length === 3;
      const seenCount = (smokeReport.phase5SeenContentTypes || []).length;
      if (projectRouteHit && seenCount >= 4) {
        setTimeout(() => {
          app.quit();
        }, 500);
      }
    }

    if (
      smokeFlow === "phase6" &&
      typeof snapshot.route === "string" &&
      snapshot.route.startsWith("/project/") &&
      snapshot.projectStatus === "content_generated" &&
      snapshot.generatedContentCount === 4
    ) {
      const projectRouteHit = snapshot.route.split("/").length === 3;
      const seenCount = (smokeReport.phase6SeenContentTypes || []).length;
      if (projectRouteHit && seenCount >= 4) {
        setTimeout(() => {
          app.quit();
        }, 500);
      }
    }

    if (
      smokeFlow === "phase6-restart" &&
      typeof snapshot.route === "string" &&
      snapshot.route.startsWith("/project/") &&
      snapshot.projectStatus === "content_generated" &&
      snapshot.generatedContentCount === 4
    ) {
      const projectRouteHit = snapshot.route.split("/").length === 3;
      const seenCount = (smokeReport.phase6SeenContentTypes || []).length;
      if (projectRouteHit && seenCount >= 4) {
        setTimeout(() => {
          app.quit();
        }, 500);
      }
    }

    if (
      smokeFlow === "phase7" &&
      typeof snapshot.route === "string" &&
      snapshot.route.startsWith("/project/") &&
      snapshot.projectStatus === "published" &&
      snapshot.publishedContentCount === 4
    ) {
      const publishRouteHit = snapshot.route.endsWith("/publish");
      const projectRouteHit = snapshot.route.split("/").length === 3;
      if (publishRouteHit || projectRouteHit) {
        setTimeout(() => {
          app.quit();
        }, 500);
      }
    }

    if (
      smokeFlow === "phase7-restart" &&
      typeof snapshot.route === "string" &&
      snapshot.route.startsWith("/project/") &&
      snapshot.projectStatus === "published" &&
      snapshot.publishedContentCount === 4
    ) {
      const publishRouteHit = snapshot.route.endsWith("/publish");
      const projectRouteHit = snapshot.route.split("/").length === 3;
      if (publishRouteHit || projectRouteHit) {
        setTimeout(() => {
          app.quit();
        }, 500);
      }
    }

    if (
      smokeFlow === "phase8" &&
      typeof snapshot.route === "string" &&
      snapshot.route.endsWith("/publish") &&
      snapshot.projectStatus === "published" &&
      snapshot.publishedContentCount === 4 &&
      snapshot.instagramCredentialPresent === true &&
      snapshot.threadsCredentialPresent === true &&
      snapshot.instagramValidation === "missing" &&
      snapshot.threadsValidation === "missing" &&
      snapshot.naverValidation === "unsupported"
    ) {
      setTimeout(() => {
        app.quit();
      }, 500);
    }

    if (
      smokeFlow === "phase8-restart" &&
      typeof snapshot.route === "string" &&
      snapshot.route.endsWith("/publish") &&
      snapshot.projectStatus === "published" &&
      snapshot.publishedContentCount === 4 &&
      snapshot.instagramCredentialPresent === true &&
      snapshot.threadsCredentialPresent === true &&
      snapshot.instagramValidation === "missing" &&
      snapshot.threadsValidation === "missing" &&
      snapshot.naverValidation === "unsupported"
    ) {
      setTimeout(() => {
        app.quit();
      }, 500);
    }

    if (
      smokeFlow === "phase9" &&
      typeof snapshot.route === "string" &&
      snapshot.route.endsWith("/publish") &&
      snapshot.projectStatus === "content_generated" &&
      snapshot.publishedContentCount === 0 &&
      snapshot.publishRunCount === 4 &&
      snapshot.latestPublishModes?.blog === "live" &&
      snapshot.latestPublishModes?.carousel === "live" &&
      snapshot.latestPublishModes?.video === "live" &&
      snapshot.latestPublishModes?.thread === "live" &&
      snapshot.latestPublishStatuses?.blog === "unsupported" &&
      snapshot.latestPublishStatuses?.carousel === "missing" &&
      snapshot.latestPublishStatuses?.video === "unsupported" &&
      snapshot.latestPublishStatuses?.thread === "missing"
    ) {
      setTimeout(() => {
        app.quit();
      }, 500);
    }

    if (
      smokeFlow === "phase9-restart" &&
      typeof snapshot.route === "string" &&
      snapshot.route.endsWith("/publish") &&
      snapshot.projectStatus === "content_generated" &&
      snapshot.publishedContentCount === 0 &&
      snapshot.publishRunCount === 4 &&
      snapshot.latestPublishModes?.blog === "live" &&
      snapshot.latestPublishModes?.carousel === "live" &&
      snapshot.latestPublishModes?.video === "live" &&
      snapshot.latestPublishModes?.thread === "live" &&
      snapshot.latestPublishStatuses?.blog === "unsupported" &&
      snapshot.latestPublishStatuses?.carousel === "missing" &&
      snapshot.latestPublishStatuses?.video === "unsupported" &&
      snapshot.latestPublishStatuses?.thread === "missing"
    ) {
      setTimeout(() => {
        app.quit();
      }, 500);
    }

    if (
      smokeFlow === "phase10" &&
      typeof snapshot.route === "string" &&
      snapshot.route.endsWith("/publish") &&
      snapshot.projectStatus === "content_generated" &&
      snapshot.publishedContentCount === 0 &&
      snapshot.publishRunCount === 2 &&
      snapshot.latestPublishModes?.blog === "live" &&
      snapshot.latestPublishModes?.video === "live" &&
      snapshot.latestPublishStatuses?.blog === "manual_ready" &&
      snapshot.latestPublishStatuses?.video === "manual_ready" &&
      snapshot.publishSummaryCounts?.manualReady === 2 &&
      snapshot.publishSummaryCounts?.blocked === 2
    ) {
      setTimeout(() => {
        app.quit();
      }, 500);
    }

    if (
      smokeFlow === "phase10-restart" &&
      typeof snapshot.route === "string" &&
      snapshot.route.endsWith("/publish") &&
      snapshot.projectStatus === "content_generated" &&
      snapshot.publishedContentCount === 0 &&
      snapshot.publishRunCount === 2 &&
      snapshot.latestPublishModes?.blog === "live" &&
      snapshot.latestPublishModes?.video === "live" &&
      snapshot.latestPublishStatuses?.blog === "manual_ready" &&
      snapshot.latestPublishStatuses?.video === "manual_ready" &&
      snapshot.publishSummaryCounts?.manualReady === 2 &&
      snapshot.publishSummaryCounts?.blocked === 2
    ) {
      setTimeout(() => {
        app.quit();
      }, 500);
    }

    return { recorded: true };
  });

  ipcMain.handle("app:run-phase2-smoke-scenario", async () => {
    const scenario = await runPhase2SmokeScenario();
    if (smokeReport) {
      smokeReport.scenario = scenario;
      writeSmokeReport();
    }
    return scenario;
  });
  ipcMain.handle("app:run-phase3-smoke-scenario", async () => {
    const scenario = await runPhase3SmokeScenario();
    if (smokeReport) {
      smokeReport.scenario = scenario;
      writeSmokeReport();
    }
    return scenario;
  });
  ipcMain.handle("app:run-phase4-smoke-scenario", async () => {
    const scenario = await runPhase4SmokeScenario();
    if (smokeReport) {
      smokeReport.scenario = scenario;
      writeSmokeReport();
    }
    return scenario;
  });

  ipcMain.handle("onboarding:select-project-folder", async () => {
    const result = await dialog.showOpenDialog(mainWindow, {
      properties: ["openDirectory", "createDirectory"],
    });
    return result.canceled ? null : result.filePaths[0];
  });

  ipcMain.handle("onboarding:check-dependencies", async () => {
    const report = {
      checkedAt: new Date().toISOString(),
      python: runDependencyCommand(
        process.env.THOHAGO_DESKTOP_PYTHON || "python",
        ["--version"]
      ),
      ffmpeg: runDependencyCommand("ffmpeg", ["-version"]),
      sidecar: sidecarManager.getStatus(),
    };
    return report;
  });

  ipcMain.handle("onboarding:complete", async (_event, payload) => {
    settingsStore.completeOnboarding(payload);
    return buildBootstrapPayload();
  });

  ipcMain.handle("sidecar:status", async () => sidecarManager.getStatus());
  ipcMain.handle("sidecar:ping", async () =>
    sidecarManager.call("system.ping", {})
  );
  ipcMain.handle("sidecar:system-status", async () =>
    sidecarManager.call("system.status", {})
  );
  ipcMain.handle("settings:list", async () =>
    settingsStore.listInspectableSettings()
  );

  ipcMain.handle("project:select-media-files", async () => {
    const result = await dialog.showOpenDialog(mainWindow, {
      properties: ["openFile", "multiSelections"],
      filters: [
        {
          name: "Media",
          extensions: ["jpg", "jpeg", "png", "webp", "mp4", "mov", "webm"],
        },
      ],
    });
    return result.canceled ? [] : result.filePaths;
  });
  ipcMain.handle("project:list", async () => projectService.listProjects());
  ipcMain.handle("project:create", async (_event, payload) =>
    projectService.createProject(payload)
  );
  ipcMain.handle("project:get", async (_event, projectId) =>
    projectService.getProject(projectId)
  );
  ipcMain.handle("project:import-media", async (_event, payload) =>
    projectService.importMedia(payload.projectId, payload.filePaths)
  );
  ipcMain.handle("project:set-hero-media", async (_event, payload) =>
    projectService.setRepresentativeMedia(payload.projectId, payload.mediaAssetId)
  );
  ipcMain.handle("project:update-media-order", async (_event, payload) =>
    projectService.updateMediaOrder(payload.projectId, payload.orderedAssetIds)
  );
  ipcMain.handle("project:build-preflight", async (_event, projectId) =>
    projectService.buildPreflight(projectId)
  );
  ipcMain.handle("project:get-generation-defaults", async (_event, projectId) =>
    projectService.getGenerationDefaults(projectId)
  );
  ipcMain.handle("project:save-generation-profile", async (_event, payload) =>
    projectService.saveGenerationProfile(payload.projectId, payload.profile)
  );

  ipcMain.handle("interview:get", async (_event, projectId) =>
    interviewService.getSession(projectId)
  );
  ipcMain.handle("interview:start", async (_event, projectId) =>
    interviewService.startInterview(projectId)
  );
  ipcMain.handle("interview:submit-answer", async (_event, payload) =>
    interviewService.submitAnswer(payload.projectId, payload.answer)
  );
  ipcMain.handle("content:generate-all", async (_event, projectId) =>
    contentGenerationService.generateAll(projectId)
  );
  ipcMain.handle("content:get-spec", async (_event, payload) =>
    contentGenerationService.getContentSpec(payload.projectId, payload.contentType)
  );
  ipcMain.handle("content:get-preview-html", async (_event, payload) =>
    contentGenerationService.getPreviewHtml(payload.projectId, payload.contentType)
  );
  ipcMain.handle("content:regenerate", async (_event, payload) =>
    contentGenerationService.regenerateContent(
      payload.projectId,
      payload.contentType,
      payload.mode
    )
  );
  ipcMain.handle("content:get-runs", async (_event, payload) =>
    contentGenerationService.getGenerationRuns(payload.projectId, payload.contentType)
  );
  ipcMain.handle("publish:run", async (_event, payload) =>
    publishService.publishContent(
      payload.projectId,
      payload.contentType,
      payload.executionMode
    )
  );
  ipcMain.handle("publish:get-runs", async (_event, projectId) =>
    publishService.getPublishRuns(projectId)
  );
  ipcMain.handle("publish:get-summary", async (_event, projectId) =>
    publishService.getPublishSummary(projectId)
  );
  ipcMain.handle("publish:run-recommended", async (_event, projectId) =>
    publishService.runRecommendedPublish(projectId)
  );
  ipcMain.handle("publish:get-credential-status", async () =>
    publishService.getCredentialStatus()
  );
  ipcMain.handle("publish:save-credentials", async (_event, payload) =>
    publishService.saveCredentials(payload)
  );
  ipcMain.handle("publish:validate-provider", async (_event, provider) =>
    publishService.validateProvider(provider)
  );
}

app.whenReady().then(async () => {
  app.name = APP_TITLE;

  appState = await createApplicationState();
  database = appState.db;
  settingsStore = appState.settings;
  sidecarManager = appState.sidecar;
  projectService = new ProjectService({
    database,
    settingsStore,
    sidecarManager,
    logger: appState.mainLog,
  });
  interviewService = new InterviewService({
    database,
    projectService,
    sidecarManager,
  });
  contentGenerationService = new ContentGenerationService({
    database,
    projectService,
    sidecarManager,
  });
  publishService = new PublishService({
    database,
    projectService,
    contentGenerationService,
    sidecarManager,
    settingsStore,
  });

  if (process.env.THOHAGO_DESKTOP_SMOKE_OUTPUT) {
    smokeReport = {
      outputPath: path.resolve(process.cwd(), process.env.THOHAGO_DESKTOP_SMOKE_OUTPUT),
      startedAt: new Date().toISOString(),
      dataDir: appState.dataDir,
      dbPath: appState.dbPath,
      snapshots: [],
      smokeFlow: process.env.THOHAGO_DESKTOP_SMOKE_FLOW || "phase1",
    };
    writeSmokeReport();
  }

  registerIpcHandlers();
  await createMainWindow();
});

process.on("uncaughtException", (error) => {
  logToConsole(`uncaughtException ${error.stack || error.message}`);
});

process.on("unhandledRejection", (error) => {
  logToConsole(`unhandledRejection ${error}`);
});

app.on("before-quit", (event) => {
  if (isQuittingGracefully) {
    return;
  }

  if (!sidecarManager) {
    isQuittingGracefully = true;
    return;
  }

  event.preventDefault();
  isQuittingGracefully = true;
  sidecarManager
    .stop()
    .catch((error) => {
      logToConsole(`sidecar stop failed during quit: ${error.message}`);
    })
    .finally(() => {
      app.exit(0);
    });
});

app.on("window-all-closed", () => {
  app.quit();
});
