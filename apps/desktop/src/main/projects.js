const fs = require("node:fs");
const path = require("node:path");
const { randomUUID } = require("node:crypto");

class ProjectService {
  constructor({ database, settingsStore, sidecarManager, logger = () => {} }) {
    this.database = database;
    this.settingsStore = settingsStore;
    this.sidecarManager = sidecarManager;
    this.logger = logger;
  }

  listProjects() {
    const rows = this.database.all(
      `
      SELECT
        p.*,
        COUNT(m.id) AS media_count,
        (
          SELECT COUNT(*)
          FROM content_specs cs
          WHERE cs.project_id = p.id AND cs.status = 'published'
        ) AS published_content_count,
        (
          SELECT status
          FROM interview_sessions s
          WHERE s.project_id = p.id
          ORDER BY s.created_at DESC
          LIMIT 1
        ) AS latest_interview_status
      FROM projects p
      LEFT JOIN media_assets m ON m.project_id = p.id
      GROUP BY p.id
      ORDER BY p.updated_at DESC, p.created_at DESC
      `
    );

    return rows.map((row) => this.formatProjectRow(row));
  }

  getProject(projectId) {
    const row = this.database.get("SELECT * FROM projects WHERE id = ?", [projectId]);
    if (!row) {
      throw new Error("project not found");
    }

    const project = this.formatProjectRow(row);
    const mediaAssets = this.database
      .all(
        "SELECT * FROM media_assets WHERE project_id = ? ORDER BY experience_order ASC, created_at ASC",
        [projectId]
      )
      .map(formatMediaRow);
    const contentSpecs = this.database
      .all(
        "SELECT * FROM content_specs WHERE project_id = ? ORDER BY content_type ASC",
        [projectId]
      )
      .map(formatContentSpecRow);
    const publishRuns = this.database
      .all(
        `
        SELECT
          r.*,
          c.content_type
        FROM publish_runs r
        JOIN content_specs c ON c.id = r.content_spec_id
        WHERE c.project_id = ?
        ORDER BY r.created_at DESC
        `,
        [projectId]
      )
      .map(formatPublishRunRow);
    const latestSession = this.database.get(
      `
      SELECT *
      FROM interview_sessions
      WHERE project_id = ?
      ORDER BY created_at DESC
      LIMIT 1
      `,
      [projectId]
    );

    return {
      ...project,
      mediaAssets,
      contentSpecs,
      generatedContentCount: contentSpecs.length,
      publishRuns,
      publishedContentCount: contentSpecs.filter((entry) => entry.status === "published").length,
      latestInterview: latestSession ? formatInterviewRow(latestSession) : null,
    };
  }

  getGenerationDefaults(projectId) {
    const project = this.getProject(projectId);
    return buildGenerationProfileDefaults(project);
  }

  createProject(payload) {
    const projectRoot = this.requireProjectRoot();
    const now = new Date().toISOString();
    const slug = slugify(payload.name || payload.shopDisplayName || "project");
    const projectId = `${slug}-${now.replace(/[-:.TZ]/g, "").slice(0, 14)}`;
    const projectFolderPath = path.join(projectRoot, projectId);
    const mediaFolderPath = path.join(projectFolderPath, "media");

    fs.mkdirSync(mediaFolderPath, { recursive: true });

    this.database.run(
      `
      INSERT INTO projects (
        id,
        name,
        shop_display_name,
        summary,
        project_folder_path,
        media_folder_path,
        status,
        created_at,
        updated_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
      `,
      [
        projectId,
        payload.name.trim(),
        payload.shopDisplayName.trim(),
        (payload.summary || "").trim(),
        projectFolderPath,
        mediaFolderPath,
        "created",
        now,
        now,
      ]
    );

    const project = this.getProject(projectId);
    this.writeProjectArtifact(project);
    return project;
  }

  importMedia(projectId, filePaths) {
    const project = this.getProject(projectId);
    if (!Array.isArray(filePaths) || filePaths.length === 0) {
      throw new Error("select at least one media file");
    }

    const existingAssets = project.mediaAssets;
    const incomingKinds = filePaths.map((filePath) =>
      detectMediaKind(path.basename(filePath))
    );
    const existingPhotoCount = existingAssets.filter((asset) => asset.kind === "photo").length;
    const existingVideoCount = existingAssets.filter((asset) => asset.kind === "video").length;
    const incomingPhotoCount = incomingKinds.filter((kind) => kind === "photo").length;
    const incomingVideoCount = incomingKinds.filter((kind) => kind === "video").length;

    if (existingPhotoCount + incomingPhotoCount > 10) {
      throw new Error("phase 2 supports up to 10 photos per project");
    }
    if (existingVideoCount + incomingVideoCount > 2) {
      throw new Error("phase 2 supports up to 2 videos per project");
    }

    let nextOrder = existingAssets.length;
    const imported = [];

    for (const filePath of filePaths) {
      const absolute = path.resolve(filePath);
      const stats = fs.statSync(absolute);
      if (!stats.isFile()) {
        continue;
      }

      const fileName = path.basename(absolute);
      const targetName = ensureUniqueFileName(project.mediaFolderPath, fileName);
      const targetPath = path.join(project.mediaFolderPath, targetName);
      fs.copyFileSync(absolute, targetPath);

      const assetId = randomUUID();
      const kind = detectMediaKind(targetName);
      this.database.run(
        `
        INSERT INTO media_assets (
          id,
          project_id,
          kind,
          source_file_path,
          file_path,
          file_name,
          mime_type,
          experience_order,
          is_hero,
          created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        `,
        [
          assetId,
          projectId,
          kind,
          absolute,
          targetPath,
          targetName,
          detectMimeType(targetName),
          nextOrder,
          0,
          new Date().toISOString(),
        ]
      );

      imported.push({
        id: assetId,
        kind,
        filePath: targetPath,
        fileName: targetName,
        experienceOrder: nextOrder,
      });
      nextOrder += 1;
    }

    if (!project.heroMediaAssetId && imported.length > 0) {
      this.setRepresentativeMedia(projectId, imported[0].id);
    }

    this.touchProject(projectId, "media_ready");
    const updated = this.getProject(projectId);
    this.writeProjectArtifact(updated);
    return updated;
  }

  updateMediaOrder(projectId, orderedAssetIds) {
    orderedAssetIds.forEach((assetId, index) => {
      this.database.run(
        "UPDATE media_assets SET experience_order = ? WHERE id = ? AND project_id = ?",
        [index, assetId, projectId]
      );
    });
    this.touchProject(projectId, "media_ready");
    const updated = this.getProject(projectId);
    this.writeProjectArtifact(updated);
    return updated;
  }

  setRepresentativeMedia(projectId, mediaAssetId) {
    this.database.run("UPDATE media_assets SET is_hero = 0 WHERE project_id = ?", [
      projectId,
    ]);
    this.database.run(
      "UPDATE media_assets SET is_hero = 1 WHERE id = ? AND project_id = ?",
      [mediaAssetId, projectId]
    );
    this.database.run(
      "UPDATE projects SET hero_media_asset_id = ?, updated_at = ? WHERE id = ?",
      [mediaAssetId, new Date().toISOString(), projectId]
    );
    const updated = this.getProject(projectId);
    this.writeProjectArtifact(updated);
    return updated;
  }

  async buildPreflight(projectId) {
    const project = this.getProject(projectId);
    if (project.mediaAssets.length === 0) {
      throw new Error("import media before running preflight");
    }

    const preflight = await this.sidecarManager.call("interview.build_preflight", {
      project_id: project.id,
      shop_display_name: project.shopDisplayName,
      media_items: project.mediaAssets.map((asset) => ({
        id: asset.id,
        kind: asset.kind,
        file_name: asset.fileName,
        file_path: asset.filePath,
        mime_type: asset.mimeType,
        experience_order: asset.experienceOrder,
        is_hero: asset.isHero,
      })),
    });

    this.database.run(
      "UPDATE projects SET preflight_json = ?, updated_at = ?, status = ? WHERE id = ?",
      [
        JSON.stringify(preflight),
        new Date().toISOString(),
        "media_ready",
        projectId,
      ]
    );

    const updated = this.getProject(projectId);
    this.writeProjectArtifact(updated);
    this.writePreflightArtifact(updated, preflight);
    return updated;
  }

  writeProjectArtifact(project) {
    const artifact = {
      id: project.id,
      name: project.name,
      shopDisplayName: project.shopDisplayName,
      summary: project.summary,
      status: project.status,
      generationProfile: project.generationProfile,
      projectFolderPath: project.projectFolderPath,
      mediaFolderPath: project.mediaFolderPath,
      heroMediaAssetId: project.heroMediaAssetId,
      mediaAssets: project.mediaAssets.map((asset) => ({
        id: asset.id,
        kind: asset.kind,
        fileName: asset.fileName,
        filePath: asset.filePath,
        experienceOrder: asset.experienceOrder,
        isHero: asset.isHero,
      })),
      updatedAt: project.updatedAt,
    };
    writeJson(path.join(project.projectFolderPath, "project.json"), artifact);
  }

  writePreflightArtifact(project, preflight) {
    writeJson(
      path.join(project.projectFolderPath, "preflight", "media_preflight.json"),
      preflight
    );
  }

  saveGenerationProfile(projectId, payload) {
    const project = this.getProject(projectId);
    const interviewStatus = project.latestInterview?.status ?? project.latestInterviewStatus;
    if (interviewStatus !== "completed") {
      throw new Error("complete the interview before configuring generation");
    }
    if (project.mediaAssets.length === 0) {
      throw new Error("import media before configuring generation");
    }

    const normalized = normalizeGenerationProfile(project, payload);
    const now = new Date().toISOString();
    this.database.run(
      `
      UPDATE projects
      SET generation_profile_json = ?, status = ?, updated_at = ?
      WHERE id = ?
      `,
      [JSON.stringify(normalized), "ready_to_generate", now, projectId]
    );

    const updated = this.getProject(projectId);
    this.writeProjectArtifact(updated);
    this.writeGenerationProfileArtifact(updated);
    return updated;
  }

  writeGenerationProfileArtifact(project) {
    if (!project.generationProfile) {
      return;
    }

    writeJson(
      path.join(project.projectFolderPath, "generation", "generation_profile.json"),
      {
        projectId: project.id,
        shopDisplayName: project.shopDisplayName,
        status: project.status,
        generationProfile: project.generationProfile,
        savedAt: project.updatedAt,
      }
    );
  }

  requireProjectRoot() {
    const projectRoot = this.settingsStore.getBootstrap().projectRootPath;
    if (!projectRoot) {
      throw new Error("complete onboarding before creating a project");
    }
    fs.mkdirSync(projectRoot, { recursive: true });
    return projectRoot;
  }

  touchProject(projectId, status) {
    this.database.run(
      "UPDATE projects SET status = ?, updated_at = ? WHERE id = ?",
      [status, new Date().toISOString(), projectId]
    );
  }

  formatProjectRow(row) {
    return formatProjectRow(row);
  }
}

class InterviewService {
  constructor({ database, projectService, sidecarManager }) {
    this.database = database;
    this.projectService = projectService;
    this.sidecarManager = sidecarManager;
  }

  getSession(projectId) {
    const row = this.database.get(
      `
      SELECT *
      FROM interview_sessions
      WHERE project_id = ?
      ORDER BY created_at DESC
      LIMIT 1
      `,
      [projectId]
    );
    return row ? formatInterviewRow(row) : null;
  }

  async startInterview(projectId) {
    let project = this.projectService.getProject(projectId);
    if (project.mediaAssets.length === 0) {
      throw new Error("import media before starting the interview");
    }
    if (!project.preflight) {
      project = await this.projectService.buildPreflight(projectId);
    }

    const existing = this.getSession(projectId);
    if (existing && existing.status !== "completed") {
      return existing;
    }

    const sessionId = randomUUID();
    const now = new Date().toISOString();
    this.database.run(
      `
      INSERT INTO interview_sessions (
        id,
        project_id,
        status,
        preflight_json,
        turn1_question,
        created_at,
        updated_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?)
      `,
      [
        sessionId,
        projectId,
        "turn_1",
        JSON.stringify(project.preflight),
        fixedOpeningQuestion(project.shopDisplayName),
        now,
        now,
      ]
    );
    this.projectService.touchProject(projectId, "interviewing");
    const session = this.getSession(projectId);
    this.writeInterviewArtifact(project, session);
    return session;
  }

  async submitAnswer(projectId, answer) {
    const trimmed = (answer || "").trim();
    if (!trimmed) {
      throw new Error("answer is required");
    }

    const session = this.getSession(projectId);
    if (!session) {
      throw new Error("start the interview before answering");
    }

    const project = this.projectService.getProject(projectId);
    const now = new Date().toISOString();

    if (!session.turn1Answer) {
      const planner = await this.sidecarManager.call("interview.plan_turn", {
        turn_index: 2,
        shop_display_name: project.shopDisplayName,
        preflight: session.preflight,
        answers: [trimmed],
      });
      this.database.run(
        `
        UPDATE interview_sessions
        SET turn1_answer = ?, turn2_question = ?, planner_turn2_json = ?, status = ?, updated_at = ?
        WHERE id = ?
        `,
        [trimmed, planner.nextQuestion, JSON.stringify(planner), "turn_2", now, session.id]
      );
    } else if (!session.turn2Answer) {
      const planner = await this.sidecarManager.call("interview.plan_turn", {
        turn_index: 3,
        shop_display_name: project.shopDisplayName,
        preflight: session.preflight,
        answers: [session.turn1Answer, trimmed],
      });
      this.database.run(
        `
        UPDATE interview_sessions
        SET turn2_answer = ?, turn3_question = ?, planner_turn3_json = ?, status = ?, updated_at = ?
        WHERE id = ?
        `,
        [trimmed, planner.nextQuestion, JSON.stringify(planner), "turn_3", now, session.id]
      );
    } else if (!session.turn3Answer) {
      this.database.run(
        `
        UPDATE interview_sessions
        SET turn3_answer = ?, status = ?, updated_at = ?
        WHERE id = ?
        `,
        [trimmed, "completed", now, session.id]
      );
      this.projectService.touchProject(projectId, "interview_completed");
    } else {
      throw new Error("interview is already complete");
    }

    const updatedProject = this.projectService.getProject(projectId);
    const updatedSession = this.getSession(projectId);
    this.writeInterviewArtifact(updatedProject, updatedSession);
    this.projectService.writeProjectArtifact(updatedProject);
    return updatedSession;
  }

  writeInterviewArtifact(project, session) {
    writeJson(
      path.join(project.projectFolderPath, "interview", "interview_session.json"),
      {
        id: session.id,
        projectId: session.projectId,
        status: session.status,
        preflight: session.preflight,
        turn1Question: session.turn1Question,
        turn1Answer: session.turn1Answer,
        turn2Question: session.turn2Question,
        turn2Answer: session.turn2Answer,
        turn3Question: session.turn3Question,
        turn3Answer: session.turn3Answer,
        plannerTurn2: session.plannerTurn2,
        plannerTurn3: session.plannerTurn3,
        updatedAt: session.updatedAt,
      }
    );
  }
}

function fixedOpeningQuestion(shopDisplayName) {
  return `${shopDisplayName}를 처음 보는 사람에게 가장 먼저 보여주고 싶은 장면이나 분위기를 설명해 주세요.`;
}

function formatProjectRow(row) {
  return {
    id: row.id,
    name: row.name,
    shopDisplayName: row.shop_display_name,
    summary: row.summary || "",
    projectFolderPath: row.project_folder_path,
    mediaFolderPath: row.media_folder_path,
    heroMediaAssetId: row.hero_media_asset_id || null,
    preflight: row.preflight_json ? JSON.parse(row.preflight_json) : null,
    generationProfile: row.generation_profile_json
      ? JSON.parse(row.generation_profile_json)
      : null,
    status: row.status,
    mediaCount:
      typeof row.media_count === "number" ? row.media_count : Number(row.media_count || 0),
    publishedContentCount:
      typeof row.published_content_count === "number"
        ? row.published_content_count
        : Number(row.published_content_count || 0),
    latestInterviewStatus: row.latest_interview_status || null,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

function buildGenerationProfileDefaults(project) {
  return {
    industry: "",
    tone: "friendly",
    contentLength: "standard",
    emphasisPoint: "",
    mustIncludeKeywords: [],
    excludedPhrases: [],
    photoPriority: project.mediaAssets
      .sort((left, right) => left.experienceOrder - right.experienceOrder)
      .filter((asset) => asset.kind === "photo")
      .map((asset) => asset.id),
    representativeMediaAssetId:
      project.heroMediaAssetId ||
      project.mediaAssets.find((asset) => asset.kind === "photo")?.id ||
      project.mediaAssets[0]?.id ||
      null,
  };
}

function normalizeGenerationProfile(project, payload) {
  const defaults = buildGenerationProfileDefaults(project);
  const mediaIds = new Set(project.mediaAssets.map((asset) => asset.id));
  const requestedPriority = Array.isArray(payload.photoPriority)
    ? payload.photoPriority
    : defaults.photoPriority;
  const photoPriority = requestedPriority.filter((mediaId) => mediaIds.has(mediaId));

  const representativeMediaAssetId =
    typeof payload.representativeMediaAssetId === "string" &&
    mediaIds.has(payload.representativeMediaAssetId)
      ? payload.representativeMediaAssetId
      : defaults.representativeMediaAssetId;

  return {
    industry: String(payload.industry || "").trim(),
    tone: normalizeTone(payload.tone),
    contentLength: normalizeContentLength(payload.contentLength),
    emphasisPoint: String(payload.emphasisPoint || "").trim(),
    mustIncludeKeywords: normalizeStringList(payload.mustIncludeKeywords),
    excludedPhrases: normalizeStringList(payload.excludedPhrases),
    photoPriority: photoPriority.length > 0 ? photoPriority : defaults.photoPriority,
    representativeMediaAssetId,
  };
}

function normalizeStringList(value) {
  if (Array.isArray(value)) {
    return value
      .map((entry) => String(entry || "").trim())
      .filter(Boolean);
  }

  return String(value || "")
    .split(/\r?\n|,/)
    .map((entry) => entry.trim())
    .filter(Boolean);
}

function normalizeTone(value) {
  const candidate = String(value || "friendly").trim().toLowerCase();
  return candidate || "friendly";
}

function normalizeContentLength(value) {
  const candidate = String(value || "standard").trim().toLowerCase();
  if (["short", "standard", "long"].includes(candidate)) {
    return candidate;
  }
  return "standard";
}

function formatMediaRow(row) {
  return {
    id: row.id,
    projectId: row.project_id,
    kind: row.kind,
    sourceFilePath: row.source_file_path,
    filePath: row.file_path,
    fileName: row.file_name,
    mimeType: row.mime_type || null,
    experienceOrder: Number(row.experience_order || 0),
    isHero: Boolean(row.is_hero),
    createdAt: row.created_at,
  };
}

function formatInterviewRow(row) {
  return {
    id: row.id,
    projectId: row.project_id,
    status: row.status,
    preflight: row.preflight_json ? JSON.parse(row.preflight_json) : null,
    turn1Question: row.turn1_question || null,
    turn1Answer: row.turn1_answer || null,
    turn2Question: row.turn2_question || null,
    turn2Answer: row.turn2_answer || null,
    turn3Question: row.turn3_question || null,
    turn3Answer: row.turn3_answer || null,
    plannerTurn2: row.planner_turn2_json ? JSON.parse(row.planner_turn2_json) : null,
    plannerTurn3: row.planner_turn3_json ? JSON.parse(row.planner_turn3_json) : null,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

function formatContentSpecRow(row) {
  return {
    id: row.id,
    projectId: row.project_id,
    contentType: row.content_type,
    spec: row.spec_json ? JSON.parse(row.spec_json) : null,
    artifactPath: row.artifact_path || null,
    previewArtifactPath: row.preview_artifact_path || null,
    status: row.status,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

function formatPublishRunRow(row) {
  return {
    id: row.id,
    contentType: row.content_type,
    platform: row.platform,
    executionMode: row.execution_mode || "mock",
    status: row.status,
    permalink: row.permalink || null,
    result: JSON.parse(row.result_json),
    artifactPath: row.artifact_path || null,
    createdAt: row.created_at,
  };
}

function slugify(input) {
  const ascii = input
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return ascii || "project";
}

function detectMediaKind(fileName) {
  const extension = path.extname(fileName).toLowerCase();
  if ([".mp4", ".mov", ".avi", ".m4v", ".webm"].includes(extension)) {
    return "video";
  }
  return "photo";
}

function detectMimeType(fileName) {
  const extension = path.extname(fileName).toLowerCase();
  const map = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".webm": "video/webm",
  };
  return map[extension] || "application/octet-stream";
}

function ensureUniqueFileName(directory, originalName) {
  const parsed = path.parse(originalName);
  let candidate = originalName;
  let attempt = 1;

  while (fs.existsSync(path.join(directory, candidate))) {
    candidate = `${parsed.name}_${attempt}${parsed.ext}`;
    attempt += 1;
  }

  return candidate;
}

function writeJson(filePath, payload) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, JSON.stringify(payload, null, 2), "utf8");
}

function fixedOpeningQuestion(shopDisplayName) {
  return `${shopDisplayName}를 처음 보는 사람이 가장 먼저 느낄 만한 장면이나 분위기를 설명해 주세요.`;
}

module.exports = {
  ProjectService,
  InterviewService,
  fixedOpeningQuestion,
};
