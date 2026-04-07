const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");
const { createDatabase } = require("../src/main/database");
const { ContentGenerationService } = require("../src/main/content-generation");
const { PublishService } = require("../src/main/publish-service");
const { ProjectService, InterviewService } = require("../src/main/projects");
const { createSecretCodec } = require("../src/main/security");
const { SettingsStore } = require("../src/main/settings");
const { SidecarProcessManager } = require("@thohago/python-sidecar");

const repoRoot = path.resolve(__dirname, "../../..");
const migrationsDir = path.join(repoRoot, "migrations", "desktop");

test("desktop settings persist onboarding state and encrypted secrets", async () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "thohago-desktop-db-"));
  const dbPath = path.join(tmpDir, "desktop.sqlite");

  const db = await createDatabase({
    dbPath,
    migrationsDir,
  });
  const settings = new SettingsStore({
    database: db,
    codec: createSecretCodec(),
  });

  assert.equal(settings.getBootstrap().onboardingCompleted, false);

  settings.completeOnboarding({
    projectRootPath: path.join(tmpDir, "projects"),
    apiKeys: {
      gemini: "gem-test-key",
      anthropic: "",
      openai: "",
    },
    dependencyCheck: {
      checkedAt: "2026-04-07T00:00:00Z",
      python: { available: true },
      ffmpeg: { available: false },
      sidecar: { state: "connected" },
    },
  });

  const bootstrap = settings.getBootstrap();
  assert.equal(bootstrap.onboardingCompleted, true);
  assert.equal(bootstrap.apiKeys.gemini, true);
  assert.equal(
    bootstrap.projectRootPath,
    path.join(tmpDir, "projects")
  );

  const secretRow = db.get("SELECT value, is_encrypted FROM settings WHERE key = ?", [
    "gemini_api_key",
  ]);
  assert.equal(secretRow.is_encrypted, 1);
  assert.notEqual(secretRow.value.includes("gem-test-key"), true);

  const reopenedDb = await createDatabase({
    dbPath,
    migrationsDir,
  });
  const reopenedSettings = new SettingsStore({
    database: reopenedDb,
    codec: createSecretCodec(),
  });

  assert.equal(reopenedSettings.getBootstrap().onboardingCompleted, true);
  assert.equal(reopenedSettings.getSecret("gemini_api_key"), "gem-test-key");
});

test("python sidecar responds to ping and status over stdio json-rpc", async () => {
  const manager = new SidecarProcessManager({
    command: process.env.THOHAGO_DESKTOP_PYTHON || "python",
    args: ["-u", "-m", "sidecar.server", "--project-root", repoRoot],
    cwd: repoRoot,
    env: {
      ...process.env,
      PYTHONPATH: [repoRoot, path.join(repoRoot, "src"), process.env.PYTHONPATH]
        .filter(Boolean)
        .join(path.delimiter),
    },
  });

  try {
    await manager.start();
    const ping = await manager.call("system.ping", {});
    const status = await manager.call("system.status", {});

    assert.equal(ping.ok, true);
    assert.equal(status.ok, true);
    assert.equal(status.project_root, repoRoot);
    assert.equal(manager.getStatus().state, "connected");
  } finally {
    await manager.stop();
  }

  assert.equal(manager.getStatus().state, "stopped");
});

test("python sidecar preserves Korean text over stdio json-rpc", async () => {
  const manager = new SidecarProcessManager({
    command: process.env.THOHAGO_DESKTOP_PYTHON || "python",
    args: ["-u", "-m", "sidecar.server", "--project-root", repoRoot],
    cwd: repoRoot,
    env: {
      ...process.env,
      PYTHONPATH: [repoRoot, path.join(repoRoot, "src"), process.env.PYTHONPATH]
        .filter(Boolean)
        .join(path.delimiter),
    },
  });

  try {
    await manager.start();
    const result = await manager.call("content.compose_blog", {
      bundle: {
        shopDisplayName: "시선을즐기다",
        summary: "프리미엄 헤드스파",
        generationProfile: {
          emphasisPoint: "프리미엄 헤드스파",
          mustIncludeKeywords: ["프리미엄 헤드스파", "부산 여행"],
          tone: "premium",
          contentLength: "standard",
          industry: "headspa",
        },
        interview: {
          turn1Answer: "캐나다에서 커플이 찾아와 특별한 경험을 원했다고 했어요.",
          turn2Answer: "헤드스파 후에 헤어 마사지를 받고 편안하게 쉬어 갔어요.",
          turn3Answer: "우리는 손님마다 맞춤형 서비스와 최신 기술을 제공합니다.",
        },
      },
    });

    assert.equal(result.title.includes("시선을즐기다"), true);
    assert.equal(result.sections[0].heading, "처음 방문했을 때 가장 먼저 느껴지는 점");
    assert.equal(result.sections[0].body.includes("캐나다에서 커플이 찾아와"), true);
    assert.equal(result.sections[1].body.includes("헤드스파 후에 헤어 마사지"), true);
    assert.equal(result.sections[2].body.includes("맞춤형 서비스"), true);
  } finally {
    await manager.stop();
  }
});

test("project, media preflight, and text-first interview persist end-to-end", async () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "thohago-desktop-phase2-"));
  const dbPath = path.join(tmpDir, "desktop.sqlite");
  const onboardingProjectRoot = path.join(tmpDir, "projects-root");
  const sourceMediaDir = path.join(tmpDir, "fixtures");
  fs.mkdirSync(sourceMediaDir, { recursive: true });
  const sourceA = path.join(sourceMediaDir, "fixture_a.jpg");
  const sourceB = path.join(sourceMediaDir, "fixture_b.jpg");
  fs.writeFileSync(sourceA, "fixture-a");
  fs.writeFileSync(sourceB, "fixture-b");

  const db = await createDatabase({
    dbPath,
    migrationsDir,
  });
  const settings = new SettingsStore({
    database: db,
    codec: createSecretCodec(),
  });
  settings.completeOnboarding({
    projectRootPath: onboardingProjectRoot,
    apiKeys: { gemini: "", anthropic: "", openai: "" },
    dependencyCheck: null,
  });

  const sidecar = new SidecarProcessManager({
    command: process.env.THOHAGO_DESKTOP_PYTHON || "python",
    args: ["-u", "-m", "sidecar.server", "--project-root", repoRoot],
    cwd: repoRoot,
    env: {
      ...process.env,
      PYTHONPATH: [repoRoot, path.join(repoRoot, "src"), process.env.PYTHONPATH]
        .filter(Boolean)
        .join(path.delimiter),
    },
  });

  await sidecar.start();
  try {
    const projectService = new ProjectService({
      database: db,
      settingsStore: settings,
      sidecarManager: sidecar,
    });
    const interviewService = new InterviewService({
      database: db,
      projectService,
      sidecarManager: sidecar,
    });

    const project = projectService.createProject({
      name: "phase2-salon",
      shopDisplayName: "Phase2 Salon",
      summary: "quiet premium care",
    });
    const withMedia = projectService.importMedia(project.id, [sourceA, sourceB]);
    assert.equal(withMedia.mediaAssets.length, 2);
    const withHero = projectService.setRepresentativeMedia(
      project.id,
      withMedia.mediaAssets[1].id
    );
    assert.equal(withHero.heroMediaAssetId, withMedia.mediaAssets[1].id);

    const withPreflight = await projectService.buildPreflight(project.id);
    assert.equal(withPreflight.preflight?.ok, true);

    let session = await interviewService.startInterview(project.id);
    assert.equal(session.status, "turn_1");
    session = await interviewService.submitAnswer(
      project.id,
      "A calm first impression matters most."
    );
    assert.equal(session.status, "turn_2");
    session = await interviewService.submitAnswer(
      project.id,
      "The service moves carefully from consultation to finish."
    );
    assert.equal(session.status, "turn_3");
    session = await interviewService.submitAnswer(
      project.id,
      "We want guests to remember the resting experience, not only the result."
    );
    assert.equal(session.status, "completed");

    const projectFolder = path.join(onboardingProjectRoot, project.id);
    assert.equal(fs.existsSync(path.join(projectFolder, "project.json")), true);
    assert.equal(
      fs.existsSync(path.join(projectFolder, "preflight", "media_preflight.json")),
      true
    );
    assert.equal(
      fs.existsSync(path.join(projectFolder, "interview", "interview_session.json")),
      true
    );

    const completedProject = projectService.getProject(project.id);
    assert.equal(completedProject.latestInterview?.status, "completed");
    assert.equal(completedProject.mediaAssets.length, 2);
  } finally {
    await sidecar.stop();
  }
});

test("generation profile persists and marks the project ready to generate", async () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "thohago-desktop-phase3-"));
  const dbPath = path.join(tmpDir, "desktop.sqlite");
  const onboardingProjectRoot = path.join(tmpDir, "projects-root");
  const sourceMediaDir = path.join(tmpDir, "fixtures");
  fs.mkdirSync(sourceMediaDir, { recursive: true });
  const sourceA = path.join(sourceMediaDir, "fixture_a.jpg");
  const sourceB = path.join(sourceMediaDir, "fixture_b.jpg");
  fs.writeFileSync(sourceA, "fixture-a");
  fs.writeFileSync(sourceB, "fixture-b");

  const db = await createDatabase({
    dbPath,
    migrationsDir,
  });
  const settings = new SettingsStore({
    database: db,
    codec: createSecretCodec(),
  });
  settings.completeOnboarding({
    projectRootPath: onboardingProjectRoot,
    apiKeys: { gemini: "", anthropic: "", openai: "" },
    dependencyCheck: null,
  });

  const sidecar = new SidecarProcessManager({
    command: process.env.THOHAGO_DESKTOP_PYTHON || "python",
    args: ["-u", "-m", "sidecar.server", "--project-root", repoRoot],
    cwd: repoRoot,
    env: {
      ...process.env,
      PYTHONPATH: [repoRoot, path.join(repoRoot, "src"), process.env.PYTHONPATH]
        .filter(Boolean)
        .join(path.delimiter),
    },
  });

  await sidecar.start();
  try {
    const projectService = new ProjectService({
      database: db,
      settingsStore: settings,
      sidecarManager: sidecar,
    });
    const interviewService = new InterviewService({
      database: db,
      projectService,
      sidecarManager: sidecar,
    });

    const project = projectService.createProject({
      name: "phase3-salon",
      shopDisplayName: "Phase3 Salon",
      summary: "generation setup test",
    });
    const withMedia = projectService.importMedia(project.id, [sourceA, sourceB]);
    await projectService.buildPreflight(project.id);
    await interviewService.startInterview(project.id);
    await interviewService.submitAnswer(project.id, "The greeting should feel calm.");
    await interviewService.submitAnswer(project.id, "The pace should feel steady and unrushed.");
    await interviewService.submitAnswer(project.id, "The owner voice should feel premium and caring.");

    const defaults = projectService.getGenerationDefaults(project.id);
    const saved = projectService.saveGenerationProfile(project.id, {
      ...defaults,
      industry: "salon",
      tone: "premium",
      contentLength: "long",
      emphasisPoint: "premium scalp care and calm consultation",
      mustIncludeKeywords: ["premium scalp care", "consultation"],
      excludedPhrases: ["cheap", "must visit"],
      representativeMediaAssetId: withMedia.mediaAssets[1].id,
      photoPriority: [withMedia.mediaAssets[1].id, withMedia.mediaAssets[0].id],
    });

    assert.equal(saved.status, "ready_to_generate");
    assert.equal(saved.generationProfile?.industry, "salon");
    assert.deepEqual(saved.generationProfile?.photoPriority, [
      withMedia.mediaAssets[1].id,
      withMedia.mediaAssets[0].id,
    ]);
    assert.equal(
      saved.generationProfile?.representativeMediaAssetId,
      withMedia.mediaAssets[1].id
    );

    const projectFolder = path.join(onboardingProjectRoot, project.id);
    assert.equal(
      fs.existsSync(path.join(projectFolder, "generation", "generation_profile.json")),
      true
    );

    const reopenedDb = await createDatabase({
      dbPath,
      migrationsDir,
    });
    const reopenedProjectService = new ProjectService({
      database: reopenedDb,
      settingsStore: settings,
      sidecarManager: sidecar,
    });
    const reopened = reopenedProjectService.getProject(project.id);
    assert.equal(reopened.status, "ready_to_generate");
    assert.equal(reopened.generationProfile?.tone, "premium");
    assert.equal(reopened.generationProfile?.contentLength, "long");
  } finally {
    await sidecar.stop();
  }
});

test("generate all content persists bundle and four content specs", async () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "thohago-desktop-phase4-"));
  const dbPath = path.join(tmpDir, "desktop.sqlite");
  const onboardingProjectRoot = path.join(tmpDir, "projects-root");
  const sourceMediaDir = path.join(tmpDir, "fixtures");
  fs.mkdirSync(sourceMediaDir, { recursive: true });
  const sourceA = path.join(sourceMediaDir, "fixture_a.jpg");
  const sourceB = path.join(sourceMediaDir, "fixture_b.jpg");
  fs.writeFileSync(sourceA, "fixture-a");
  fs.writeFileSync(sourceB, "fixture-b");

  const db = await createDatabase({
    dbPath,
    migrationsDir,
  });
  const settings = new SettingsStore({
    database: db,
    codec: createSecretCodec(),
  });
  settings.completeOnboarding({
    projectRootPath: onboardingProjectRoot,
    apiKeys: { gemini: "", anthropic: "", openai: "" },
    dependencyCheck: null,
  });

  const sidecar = new SidecarProcessManager({
    command: process.env.THOHAGO_DESKTOP_PYTHON || "python",
    args: ["-u", "-m", "sidecar.server", "--project-root", repoRoot],
    cwd: repoRoot,
    env: {
      ...process.env,
      PYTHONPATH: [repoRoot, path.join(repoRoot, "src"), process.env.PYTHONPATH]
        .filter(Boolean)
        .join(path.delimiter),
    },
  });

  await sidecar.start();
  try {
    const projectService = new ProjectService({
      database: db,
      settingsStore: settings,
      sidecarManager: sidecar,
    });
    const interviewService = new InterviewService({
      database: db,
      projectService,
      sidecarManager: sidecar,
    });
    const contentGenerationService = new ContentGenerationService({
      database: db,
      projectService,
      sidecarManager: sidecar,
    });

    const project = projectService.createProject({
      name: "phase4-salon",
      shopDisplayName: "Phase4 Salon",
      summary: "content generation test",
    });
    projectService.importMedia(project.id, [sourceA, sourceB]);
    await projectService.buildPreflight(project.id);
    await interviewService.startInterview(project.id);
    await interviewService.submitAnswer(project.id, "First impressions should feel calm.");
    await interviewService.submitAnswer(project.id, "The visit should feel structured and premium.");
    await interviewService.submitAnswer(project.id, "The owner voice should be distinct and memorable.");

    const defaults = projectService.getGenerationDefaults(project.id);
    projectService.saveGenerationProfile(project.id, {
      ...defaults,
      industry: "salon",
      tone: "premium",
      contentLength: "standard",
      emphasisPoint: "premium scalp-care and calm consultation",
      mustIncludeKeywords: ["premium scalp care", "calm consultation"],
      excludedPhrases: ["cheap", "must visit"],
    });

    const generated = await contentGenerationService.generateAll(project.id);
    assert.equal(generated.status, "content_generated");
    assert.equal(generated.generatedContentCount, 4);

    const projectFolder = path.join(onboardingProjectRoot, project.id, "generated");
    assert.equal(fs.existsSync(path.join(projectFolder, "content_bundle.json")), true);
    assert.equal(fs.existsSync(path.join(projectFolder, "blog_spec.json")), true);
    assert.equal(fs.existsSync(path.join(projectFolder, "blog_preview.html")), true);
    assert.equal(fs.existsSync(path.join(projectFolder, "carousel_spec.json")), true);
    assert.equal(fs.existsSync(path.join(projectFolder, "video_spec.json")), true);
    assert.equal(fs.existsSync(path.join(projectFolder, "thread_spec.json")), true);
  } finally {
    await sidecar.stop();
  }
});

test("preview artifacts are persisted for all generated content types", async () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "thohago-desktop-phase5-"));
  const dbPath = path.join(tmpDir, "desktop.sqlite");
  const onboardingProjectRoot = path.join(tmpDir, "projects-root");
  const sourceMediaDir = path.join(tmpDir, "fixtures");
  fs.mkdirSync(sourceMediaDir, { recursive: true });
  const sourceA = path.join(sourceMediaDir, "fixture_a.jpg");
  const sourceB = path.join(sourceMediaDir, "fixture_b.jpg");
  fs.writeFileSync(sourceA, "fixture-a");
  fs.writeFileSync(sourceB, "fixture-b");

  const db = await createDatabase({
    dbPath,
    migrationsDir,
  });
  const settings = new SettingsStore({
    database: db,
    codec: createSecretCodec(),
  });
  settings.completeOnboarding({
    projectRootPath: onboardingProjectRoot,
    apiKeys: { gemini: "", anthropic: "", openai: "" },
    dependencyCheck: null,
  });

  const sidecar = new SidecarProcessManager({
    command: process.env.THOHAGO_DESKTOP_PYTHON || "python",
    args: ["-u", "-m", "sidecar.server", "--project-root", repoRoot],
    cwd: repoRoot,
    env: {
      ...process.env,
      PYTHONPATH: [repoRoot, path.join(repoRoot, "src"), process.env.PYTHONPATH]
        .filter(Boolean)
        .join(path.delimiter),
    },
  });

  await sidecar.start();
  try {
    const projectService = new ProjectService({
      database: db,
      settingsStore: settings,
      sidecarManager: sidecar,
    });
    const interviewService = new InterviewService({
      database: db,
      projectService,
      sidecarManager: sidecar,
    });
    const contentGenerationService = new ContentGenerationService({
      database: db,
      projectService,
      sidecarManager: sidecar,
    });

    const project = projectService.createProject({
      name: "phase5-salon",
      shopDisplayName: "Phase5 Salon",
      summary: "preview artifact test",
    });
    projectService.importMedia(project.id, [sourceA, sourceB]);
    await projectService.buildPreflight(project.id);
    await interviewService.startInterview(project.id);
    await interviewService.submitAnswer(project.id, "First impressions should feel calm.");
    await interviewService.submitAnswer(project.id, "The service should feel structured.");
    await interviewService.submitAnswer(project.id, "The owner voice should feel premium.");
    const defaults = projectService.getGenerationDefaults(project.id);
    projectService.saveGenerationProfile(project.id, {
      ...defaults,
      industry: "salon",
      tone: "premium",
      contentLength: "standard",
      emphasisPoint: "premium scalp care",
      mustIncludeKeywords: ["premium scalp care"],
      excludedPhrases: ["cheap"],
    });

    await contentGenerationService.generateAll(project.id);
    const specs = projectService.getProject(project.id).contentSpecs;
    assert.equal(specs.length, 4);
    for (const entry of specs) {
      assert.equal(Boolean(entry.previewArtifactPath), true);
      assert.equal(fs.existsSync(entry.previewArtifactPath), true);
    }
  } finally {
    await sidecar.stop();
  }
});

test("bounded regeneration persists run history and updates latest content", async () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "thohago-desktop-phase6-"));
  const dbPath = path.join(tmpDir, "desktop.sqlite");
  const onboardingProjectRoot = path.join(tmpDir, "projects-root");
  const sourceMediaDir = path.join(tmpDir, "fixtures");
  fs.mkdirSync(sourceMediaDir, { recursive: true });
  const sourceA = path.join(sourceMediaDir, "fixture_a.jpg");
  const sourceB = path.join(sourceMediaDir, "fixture_b.jpg");
  fs.writeFileSync(sourceA, "fixture-a");
  fs.writeFileSync(sourceB, "fixture-b");

  const db = await createDatabase({
    dbPath,
    migrationsDir,
  });
  const settings = new SettingsStore({
    database: db,
    codec: createSecretCodec(),
  });
  settings.completeOnboarding({
    projectRootPath: onboardingProjectRoot,
    apiKeys: { gemini: "", anthropic: "", openai: "" },
    dependencyCheck: null,
  });

  const sidecar = new SidecarProcessManager({
    command: process.env.THOHAGO_DESKTOP_PYTHON || "python",
    args: ["-u", "-m", "sidecar.server", "--project-root", repoRoot],
    cwd: repoRoot,
    env: {
      ...process.env,
      PYTHONPATH: [repoRoot, path.join(repoRoot, "src"), process.env.PYTHONPATH]
        .filter(Boolean)
        .join(path.delimiter),
    },
  });

  await sidecar.start();
  try {
    const projectService = new ProjectService({
      database: db,
      settingsStore: settings,
      sidecarManager: sidecar,
    });
    const interviewService = new InterviewService({
      database: db,
      projectService,
      sidecarManager: sidecar,
    });
    const contentGenerationService = new ContentGenerationService({
      database: db,
      projectService,
      sidecarManager: sidecar,
    });

    const project = projectService.createProject({
      name: "phase6-salon",
      shopDisplayName: "Phase6 Salon",
      summary: "bounded regeneration test",
    });
    projectService.importMedia(project.id, [sourceA, sourceB]);
    await projectService.buildPreflight(project.id);
    await interviewService.startInterview(project.id);
    await interviewService.submitAnswer(project.id, "First impression should feel calm.");
    await interviewService.submitAnswer(project.id, "The experience should feel structured.");
    await interviewService.submitAnswer(project.id, "The owner voice should feel premium.");
    const defaults = projectService.getGenerationDefaults(project.id);
    projectService.saveGenerationProfile(project.id, {
      ...defaults,
      industry: "salon",
      tone: "premium",
      contentLength: "standard",
      emphasisPoint: "premium scalp care",
      mustIncludeKeywords: ["premium scalp care"],
      excludedPhrases: ["cheap"],
    });

    await contentGenerationService.generateAll(project.id);
    const before = contentGenerationService.getContentSpec(project.id, "blog");
    const updatedProject = await contentGenerationService.regenerateContent(
      project.id,
      "blog",
      "premium"
    );
    const after = updatedProject.contentSpecs.find((entry) => entry.contentType === "blog");
    const runs = contentGenerationService.getGenerationRuns(project.id, "blog");

    assert.equal(runs.length >= 2, true);
    assert.equal(runs[0].mode, "premium");
    assert.equal(Boolean(runs[0].previewArtifactPath), true);
    assert.equal(fs.existsSync(runs[0].previewArtifactPath), true);
    assert.notEqual(JSON.stringify(before.spec), JSON.stringify(after.spec));
  } finally {
    await sidecar.stop();
  }
});

test("mock publishing persists publish runs and marks the project published", async () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "thohago-desktop-phase7-"));
  const dbPath = path.join(tmpDir, "desktop.sqlite");
  const onboardingProjectRoot = path.join(tmpDir, "projects-root");
  const sourceMediaDir = path.join(tmpDir, "fixtures");
  fs.mkdirSync(sourceMediaDir, { recursive: true });
  const sourceA = path.join(sourceMediaDir, "fixture_a.jpg");
  const sourceB = path.join(sourceMediaDir, "fixture_b.jpg");
  fs.writeFileSync(sourceA, "fixture-a");
  fs.writeFileSync(sourceB, "fixture-b");

  const db = await createDatabase({
    dbPath,
    migrationsDir,
  });
  const settings = new SettingsStore({
    database: db,
    codec: createSecretCodec(),
  });
  settings.completeOnboarding({
    projectRootPath: onboardingProjectRoot,
    apiKeys: { gemini: "", anthropic: "", openai: "" },
    dependencyCheck: null,
  });

  const sidecar = new SidecarProcessManager({
    command: process.env.THOHAGO_DESKTOP_PYTHON || "python",
    args: ["-u", "-m", "sidecar.server", "--project-root", repoRoot],
    cwd: repoRoot,
    env: {
      ...process.env,
      PYTHONPATH: [repoRoot, path.join(repoRoot, "src"), process.env.PYTHONPATH]
        .filter(Boolean)
        .join(path.delimiter),
    },
  });

  await sidecar.start();
  try {
    const projectService = new ProjectService({
      database: db,
      settingsStore: settings,
      sidecarManager: sidecar,
    });
    const interviewService = new InterviewService({
      database: db,
      projectService,
      sidecarManager: sidecar,
    });
    const contentGenerationService = new ContentGenerationService({
      database: db,
      projectService,
      sidecarManager: sidecar,
    });
    const publishService = new PublishService({
      database: db,
      projectService,
      contentGenerationService,
      sidecarManager: sidecar,
      settingsStore: settings,
    });

    const project = projectService.createProject({
      name: "phase7-salon",
      shopDisplayName: "Phase7 Salon",
      summary: "mock publishing test",
    });
    projectService.importMedia(project.id, [sourceA, sourceB]);
    await projectService.buildPreflight(project.id);
    await interviewService.startInterview(project.id);
    await interviewService.submitAnswer(project.id, "First impressions should feel calm.");
    await interviewService.submitAnswer(project.id, "The service should feel structured.");
    await interviewService.submitAnswer(project.id, "The owner voice should feel premium.");
    const defaults = projectService.getGenerationDefaults(project.id);
    projectService.saveGenerationProfile(project.id, {
      ...defaults,
      industry: "salon",
      tone: "premium",
      contentLength: "standard",
      emphasisPoint: "premium scalp care",
      mustIncludeKeywords: ["premium scalp care"],
      excludedPhrases: ["cheap"],
    });
    await contentGenerationService.generateAll(project.id);

    await publishService.publishContent(project.id, "blog");
    await publishService.publishContent(project.id, "carousel");
    await publishService.publishContent(project.id, "video");
    const publishedProject = await publishService.publishContent(project.id, "thread");

    assert.equal(publishedProject.status, "published");
    assert.equal(publishedProject.publishedContentCount, 4);
    const runs = publishService.getPublishRuns(project.id);
    assert.equal(runs.length, 4);
    for (const run of runs) {
      assert.equal(Boolean(run.artifactPath), true);
      assert.equal(fs.existsSync(run.artifactPath), true);
      assert.equal(run.status, "published");
    }
  } finally {
    await sidecar.stop();
  }
});

test("live publish credential status and validation results persist across restart", async () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "thohago-desktop-phase8-"));
  const dbPath = path.join(tmpDir, "desktop.sqlite");

  const db = await createDatabase({
    dbPath,
    migrationsDir,
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
      PYTHONPATH: [repoRoot, path.join(repoRoot, "src"), process.env.PYTHONPATH]
        .filter(Boolean)
        .join(path.delimiter),
    },
  });

  await sidecar.start();
  try {
    const publishService = new PublishService({
      database: db,
      projectService: null,
      contentGenerationService: null,
      sidecarManager: sidecar,
      settingsStore: settings,
    });

    const saved = publishService.saveCredentials({
      graphMetaAccessToken: "phase8-test-instagram-token",
      instagramBusinessAccountId: "17841400000000000",
      facebookPageId: "",
      instagramGraphVersion: "v23.0",
      threadsAccessToken: "phase8-test-threads-token",
      threadsUserId: "1234567890",
      naverLiveNote: "Manual Naver live setup note",
    });
    assert.equal(saved.instagram.accessTokenPresent, true);
    assert.equal(saved.threads.accessTokenPresent, true);
    assert.equal(saved.naver.liveNotePresent, true);
    assert.equal(saved.naver.naverLiveNote, "Manual Naver live setup note");

    const instagram = await publishService.validateProvider("instagram");
    const threads = await publishService.validateProvider("threads");
    const naver = await publishService.validateProvider("naver");

    assert.equal(instagram.validation.instagram?.status, "missing");
    assert.equal(threads.validation.threads?.status, "missing");
    assert.equal(naver.validation.naver?.status, "unsupported");

    const secretRow = db.get("SELECT value, is_encrypted FROM settings WHERE key = ?", [
      "graph_meta_access_token",
    ]);
    assert.equal(secretRow.is_encrypted, 1);
    assert.notEqual(secretRow.value.includes("phase8-test-instagram-token"), true);

    const reopenedDb = await createDatabase({
      dbPath,
      migrationsDir,
    });
    const reopenedSettings = new SettingsStore({
      database: reopenedDb,
      codec: createSecretCodec(),
    });
    const reopened = reopenedSettings.getPublishCredentialStatus();
    assert.equal(reopened.instagram.accessTokenPresent, true);
    assert.equal(reopened.instagram.instagramBusinessAccountId, "17841400000000000");
    assert.equal(reopened.threads.accessTokenPresent, true);
    assert.equal(reopened.threads.threadsUserId, "1234567890");
    assert.equal(reopened.naver.liveNotePresent, true);
    assert.equal(reopened.naver.naverLiveNote, "Manual Naver live setup note");
    assert.equal(reopened.validation.instagram?.status, "missing");
    assert.equal(reopened.validation.threads?.status, "missing");
    assert.equal(reopened.validation.naver?.status, "unsupported");
  } finally {
    await sidecar.stop();
  }
});

test("live publish attempts persist execution mode, artifacts, and provider results", async () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "thohago-desktop-phase9-"));
  const dbPath = path.join(tmpDir, "desktop.sqlite");
  const onboardingProjectRoot = path.join(tmpDir, "projects-root");
  const sourceMediaDir = path.join(tmpDir, "fixtures");
  fs.mkdirSync(sourceMediaDir, { recursive: true });
  const sourceA = path.join(sourceMediaDir, "fixture_a.jpg");
  const sourceB = path.join(sourceMediaDir, "fixture_b.jpg");
  fs.writeFileSync(sourceA, "fixture-a");
  fs.writeFileSync(sourceB, "fixture-b");

  const db = await createDatabase({
    dbPath,
    migrationsDir,
  });
  const settings = new SettingsStore({
    database: db,
    codec: createSecretCodec(),
  });
  settings.completeOnboarding({
    projectRootPath: onboardingProjectRoot,
    apiKeys: { gemini: "", anthropic: "", openai: "" },
    dependencyCheck: null,
  });

  const sidecar = new SidecarProcessManager({
    command: process.env.THOHAGO_DESKTOP_PYTHON || "python",
    args: ["-u", "-m", "sidecar.server", "--project-root", repoRoot],
    cwd: repoRoot,
    env: {
      ...process.env,
      PYTHONPATH: [repoRoot, path.join(repoRoot, "src"), process.env.PYTHONPATH]
        .filter(Boolean)
        .join(path.delimiter),
    },
  });

  await sidecar.start();
  try {
    const projectService = new ProjectService({
      database: db,
      settingsStore: settings,
      sidecarManager: sidecar,
    });
    const interviewService = new InterviewService({
      database: db,
      projectService,
      sidecarManager: sidecar,
    });
    const contentGenerationService = new ContentGenerationService({
      database: db,
      projectService,
      sidecarManager: sidecar,
    });

    const project = projectService.createProject({
      name: "phase9-salon",
      shopDisplayName: "Phase9 Salon",
      summary: "live publish execution test",
    });
    projectService.importMedia(project.id, [sourceA, sourceB]);
    await projectService.buildPreflight(project.id);
    await interviewService.startInterview(project.id);
    await interviewService.submitAnswer(project.id, "First impressions should feel calm.");
    await interviewService.submitAnswer(project.id, "The service should feel structured.");
    await interviewService.submitAnswer(project.id, "The owner voice should feel premium.");
    const defaults = projectService.getGenerationDefaults(project.id);
    projectService.saveGenerationProfile(project.id, {
      ...defaults,
      industry: "salon",
      tone: "premium",
      contentLength: "standard",
      emphasisPoint: "premium scalp care",
      mustIncludeKeywords: ["premium scalp care"],
      excludedPhrases: ["cheap"],
    });
    await contentGenerationService.generateAll(project.id);

    settings.savePublishCredentials({
      graphMetaAccessToken: "phase9-live-instagram-token",
      instagramBusinessAccountId: "17841400000000000",
      facebookPageId: "fb-page-123",
      instagramGraphVersion: "v23.0",
      threadsAccessToken: "phase9-live-threads-token",
      threadsUserId: "threads-user-123",
      naverLiveNote: "manual note",
    });

    let capturedCall = null;
    const fakePublishSidecar = {
      async call(method, payload) {
        capturedCall = { method, payload };
        return {
          provider: "instagram_graph",
          status: "error",
          message: "expired token",
        };
      },
    };

    const publishService = new PublishService({
      database: db,
      projectService,
      contentGenerationService,
      sidecarManager: fakePublishSidecar,
      settingsStore: settings,
    });

    const updatedProject = await publishService.publishContent(project.id, "carousel", "live");
    assert.equal(updatedProject.status, "content_generated");

    const runs = publishService.getPublishRuns(project.id);
    assert.equal(runs.length, 1);
    assert.equal(runs[0].executionMode, "live");
    assert.equal(runs[0].status, "error");
    assert.equal(runs[0].result.message, "expired token");
    assert.equal(Boolean(runs[0].artifactPath), true);
    assert.equal(fs.existsSync(runs[0].artifactPath), true);

    assert.equal(capturedCall.method, "publish.instagram_carousel");
    assert.equal(capturedCall.payload.execution_mode, "live");
    assert.equal(capturedCall.payload.graph_meta_access_token, "phase9-live-instagram-token");
    assert.equal(capturedCall.payload.facebook_page_id, "fb-page-123");
    assert.equal(Array.isArray(capturedCall.payload.image_paths), true);
    assert.equal(capturedCall.payload.image_paths.length >= 1, true);
    assert.equal(typeof capturedCall.payload.caption, "string");
  } finally {
    await sidecar.stop();
  }
});

test("publish summary and recommended publish create manual handoff artifacts", async () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "thohago-desktop-phase10-"));
  const dbPath = path.join(tmpDir, "desktop.sqlite");
  const onboardingProjectRoot = path.join(tmpDir, "projects-root");
  const sourceMediaDir = path.join(tmpDir, "fixtures");
  fs.mkdirSync(sourceMediaDir, { recursive: true });
  const sourceA = path.join(sourceMediaDir, "fixture_a.jpg");
  const sourceB = path.join(sourceMediaDir, "fixture_b.jpg");
  fs.writeFileSync(sourceA, "fixture-a");
  fs.writeFileSync(sourceB, "fixture-b");

  const db = await createDatabase({
    dbPath,
    migrationsDir,
  });
  const settings = new SettingsStore({
    database: db,
    codec: createSecretCodec(),
  });
  settings.completeOnboarding({
    projectRootPath: onboardingProjectRoot,
    apiKeys: { gemini: "", anthropic: "", openai: "" },
    dependencyCheck: null,
  });

  const sidecar = new SidecarProcessManager({
    command: process.env.THOHAGO_DESKTOP_PYTHON || "python",
    args: ["-u", "-m", "sidecar.server", "--project-root", repoRoot],
    cwd: repoRoot,
    env: {
      ...process.env,
      PYTHONPATH: [repoRoot, path.join(repoRoot, "src"), process.env.PYTHONPATH]
        .filter(Boolean)
        .join(path.delimiter),
    },
  });

  await sidecar.start();
  try {
    const projectService = new ProjectService({
      database: db,
      settingsStore: settings,
      sidecarManager: sidecar,
    });
    const interviewService = new InterviewService({
      database: db,
      projectService,
      sidecarManager: sidecar,
    });
    const contentGenerationService = new ContentGenerationService({
      database: db,
      projectService,
      sidecarManager: sidecar,
    });
    const publishService = new PublishService({
      database: db,
      projectService,
      contentGenerationService,
      sidecarManager: sidecar,
      settingsStore: settings,
    });

    const project = projectService.createProject({
      name: "phase10-salon",
      shopDisplayName: "Phase10 Salon",
      summary: "publish ux hardening test",
    });
    projectService.importMedia(project.id, [sourceA, sourceB]);
    await projectService.buildPreflight(project.id);
    await interviewService.startInterview(project.id);
    await interviewService.submitAnswer(project.id, "First impressions should feel calm.");
    await interviewService.submitAnswer(project.id, "The service should feel structured.");
    await interviewService.submitAnswer(project.id, "The owner voice should feel premium.");
    const defaults = projectService.getGenerationDefaults(project.id);
    projectService.saveGenerationProfile(project.id, {
      ...defaults,
      industry: "salon",
      tone: "premium",
      contentLength: "standard",
      emphasisPoint: "premium scalp care",
      mustIncludeKeywords: ["premium scalp care"],
      excludedPhrases: ["cheap"],
    });
    await contentGenerationService.generateAll(project.id);

    publishService.saveCredentials({
      graphMetaAccessToken: "phase10-instagram-token",
      instagramBusinessAccountId: "17841400000000000",
      facebookPageId: "",
      instagramGraphVersion: "v23.0",
      threadsAccessToken: "phase10-threads-token",
      threadsUserId: "1234567890",
      naverLiveNote: "manual note",
    });
    await publishService.validateProvider("instagram");
    await publishService.validateProvider("threads");
    await publishService.validateProvider("naver");

    const summaryBefore = publishService.getPublishSummary(project.id);
    assert.equal(summaryBefore.counts.manualReady, 2);
    assert.equal(summaryBefore.counts.blocked, 2);

    const recommended = await publishService.runRecommendedPublish(project.id);
    assert.deepEqual(recommended.attemptedContentTypes.sort(), ["blog", "video"]);
    assert.equal(recommended.summary.counts.manualReady, 2);

    const runs = publishService.getPublishRuns(project.id);
    assert.equal(runs.length, 2);
    assert.equal(runs.every((run) => run.executionMode === "live"), true);
    assert.equal(runs.every((run) => run.status === "manual_ready"), true);

    const blogRun = runs.find((run) => run.contentType === "blog");
    const videoRun = runs.find((run) => run.contentType === "video");
    assert.equal(Array.isArray(blogRun.result.manualArtifactPaths), true);
    assert.equal(blogRun.result.manualArtifactPaths.length >= 1, true);
    assert.equal(Array.isArray(videoRun.result.manualArtifactPaths), true);
    assert.equal(videoRun.result.manualArtifactPaths.length >= 2, true);
    for (const filePath of [...blogRun.result.manualArtifactPaths, ...videoRun.result.manualArtifactPaths]) {
      assert.equal(fs.existsSync(filePath), true);
    }
  } finally {
    await sidecar.stop();
  }
});
