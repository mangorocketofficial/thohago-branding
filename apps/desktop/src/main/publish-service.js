const fs = require("node:fs");
const path = require("node:path");
const { randomUUID } = require("node:crypto");

class PublishService {
  constructor({
    database,
    projectService,
    contentGenerationService,
    sidecarManager,
    settingsStore,
  }) {
    this.database = database;
    this.projectService = projectService;
    this.contentGenerationService = contentGenerationService;
    this.sidecarManager = sidecarManager;
    this.settingsStore = settingsStore;
  }

  async publishContent(projectId, contentType, executionMode = "mock") {
    const project = this.projectService.getProject(projectId);
    const content = this.contentGenerationService.getContentSpec(projectId, contentType);
    if (!content) {
      throw new Error(`generate ${contentType} before publishing it`);
    }

    const normalizedExecutionMode = normalizeExecutionMode(executionMode);
    const method = {
      blog: "publish.naver_blog",
      carousel: "publish.instagram_carousel",
      video: "publish.instagram_reels",
      thread: "publish.threads",
    }[contentType];
    const platform = {
      blog: "naver_blog",
      carousel: "instagram_carousel",
      video: "instagram_reels",
      thread: "threads",
    }[contentType];

    const payload = buildPublishPayload({
      project,
      content,
      executionMode: normalizedExecutionMode,
      credentials: this.settingsStore.getPublishCredentials(),
    });

    let result;
    try {
      result = await this.sidecarManager.call(method, payload);
    } catch (error) {
      result = {
        provider: platform,
        status: "error",
        message: error instanceof Error ? error.message : String(error),
      };
    }

    const normalizedResult = {
      ...result,
      status: normalizePublishStatus(result?.status),
      executionMode: normalizedExecutionMode,
    };

    const manualArtifactPaths = writeManualHandoffArtifacts(
      project.projectFolderPath,
      contentType,
      normalizedExecutionMode,
      normalizedResult
    );
    if (manualArtifactPaths.length > 0) {
      normalizedResult.manualArtifactPaths = manualArtifactPaths;
    }

    const artifacts = getPublishArtifactPaths(
      project.projectFolderPath,
      contentType,
      normalizedExecutionMode,
      normalizedResult.status
    );
    fs.mkdirSync(path.dirname(artifacts.latestPath), { recursive: true });
    fs.mkdirSync(path.dirname(artifacts.archivedPath), { recursive: true });
    fs.writeFileSync(
      artifacts.latestPath,
      JSON.stringify(normalizedResult, null, 2),
      "utf8"
    );
    fs.writeFileSync(
      artifacts.archivedPath,
      JSON.stringify(normalizedResult, null, 2),
      "utf8"
    );

    const nextContentStatus = resolveContentStatus(content.status, normalizedResult.status);
    this.database.run(
      "UPDATE content_specs SET status = ?, updated_at = ? WHERE id = ?",
      [nextContentStatus, new Date().toISOString(), content.id]
    );
    this.database.run(
      `
      INSERT INTO publish_runs (
        id,
        content_spec_id,
        platform,
        execution_mode,
        status,
        permalink,
        result_json,
        artifact_path,
        created_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
      `,
      [
        randomUUID(),
        content.id,
        platform,
        normalizedExecutionMode,
        normalizedResult.status,
        normalizedResult.permalink || normalizedResult.url || null,
        JSON.stringify(normalizedResult),
        artifacts.archivedPath,
        new Date().toISOString(),
      ]
    );

    this.updateProjectPublishStatus(projectId);
    return this.projectService.getProject(projectId);
  }

  getPublishRuns(projectId) {
    return this.database
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
      .map((row) => ({
        id: row.id,
        contentType: row.content_type,
        platform: row.platform,
        executionMode: row.execution_mode || "mock",
        status: row.status,
        permalink: row.permalink || null,
        result: JSON.parse(row.result_json),
        artifactPath: row.artifact_path || null,
        createdAt: row.created_at,
      }));
  }

  getLatestPublishMap(projectId) {
    const runs = this.getPublishRuns(projectId);
    const map = {};
    for (const run of runs) {
      if (!map[run.contentType]) {
        map[run.contentType] = run;
      }
    }
    return map;
  }

  getPublishSummary(projectId) {
    const project = this.projectService.getProject(projectId);
    const credentialStatus = this.getCredentialStatus();
    const latestPublishMap = this.getLatestPublishMap(projectId);

    const items = project.contentSpecs.map((content) => {
      const latestRun = latestPublishMap[content.contentType] || null;
      const summary = buildPublishItemSummary({
        content,
        latestRun,
        credentialStatus,
      });
      return summary;
    });

    return {
      projectId,
      counts: {
        total: items.length,
        manualReady: items.filter((item) => item.liveStatus === "manual_ready").length,
        liveReady: items.filter((item) => item.liveStatus === "ready").length,
        blocked: items.filter((item) => item.liveStatus === "blocked").length,
        attention: items.filter((item) => item.liveStatus === "attention").length,
        published: items.filter((item) => item.latestRun?.status === "published").length,
      },
      items,
    };
  }

  async runRecommendedPublish(projectId) {
    const summary = this.getPublishSummary(projectId);
    const attempted = [];
    for (const item of summary.items) {
      if (!item.canRunLiveRecommended) {
        continue;
      }
      await this.publishContent(projectId, item.contentType, "live");
      attempted.push(item.contentType);
    }
    return {
      project: this.projectService.getProject(projectId),
      attemptedContentTypes: attempted,
      summary: this.getPublishSummary(projectId),
    };
  }

  updateProjectPublishStatus(projectId) {
    const rows = this.database.all(
      "SELECT status FROM content_specs WHERE project_id = ?",
      [projectId]
    );
    const allPublished =
      rows.length >= 4 && rows.every((row) => String(row.status) === "published");
    this.database.run(
      "UPDATE projects SET status = ?, updated_at = ? WHERE id = ?",
      [allPublished ? "published" : "content_generated", new Date().toISOString(), projectId]
    );
  }

  saveCredentials(payload) {
    this.settingsStore.savePublishCredentials(payload);
    return this.settingsStore.getPublishCredentialStatus();
  }

  getCredentialStatus() {
    return this.settingsStore.getPublishCredentialStatus();
  }

  async validateProvider(provider) {
    const credentials = this.settingsStore.getPublishCredentials();
    let result;

    if (provider === "instagram") {
      result = await this.sidecarManager.call("publish.validate_instagram", {
        graph_meta_access_token: credentials.graphMetaAccessToken,
        instagram_business_account_id: credentials.instagramBusinessAccountId,
        facebook_page_id: credentials.facebookPageId,
        instagram_graph_version: credentials.instagramGraphVersion,
      });
    } else if (provider === "threads") {
      result = await this.sidecarManager.call("publish.validate_threads", {
        threads_access_token: credentials.threadsAccessToken,
        threads_user_id:
          credentials.threadsUserId || credentials.instagramBusinessAccountId,
        facebook_page_id: credentials.facebookPageId,
        instagram_graph_version: credentials.instagramGraphVersion,
      });
    } else if (provider === "naver") {
      result = await this.sidecarManager.call("publish.validate_naver", {
        naver_live_note: credentials.naverLiveNote,
      });
    } else {
      throw new Error(`unsupported publish provider: ${provider}`);
    }

    this.settingsStore.setPublishValidationResult(provider, result);
    return {
      ...this.settingsStore.getPublishCredentialStatus(),
      lastValidation: result,
    };
  }
}

function buildPublishPayload({ project, content, executionMode, credentials }) {
  const photoAssets = project.mediaAssets.filter((asset) => asset.kind === "photo");
  const videoAssets = project.mediaAssets.filter((asset) => asset.kind === "video");
  const representativePhoto =
    project.mediaAssets.find((asset) => asset.id === project.generationProfile?.representativeMediaAssetId) ||
    photoAssets.find((asset) => asset.isHero) ||
    photoAssets[0] ||
    null;
  const preferredPhotoAssets = selectPreferredPhotoAssets(project, content, photoAssets);

  return {
    project_id: project.id,
    shop_display_name: project.shopDisplayName,
    content_type: content.contentType,
    execution_mode: executionMode,
    spec: content.spec,
    spec_artifact_path: content.artifactPath,
    preview_artifact_path: content.previewArtifactPath,
    caption: buildCaptionForContent(content.contentType, content.spec),
    text: buildThreadPublishText(content.spec),
    image_paths: preferredPhotoAssets.map((asset) => asset.filePath),
    video_path: selectVideoPath(project, videoAssets),
    representative_image_path: representativePhoto?.filePath || null,
    representative_video_path: videoAssets[0]?.filePath || null,
    graph_meta_access_token: credentials.graphMetaAccessToken,
    instagram_business_account_id: credentials.instagramBusinessAccountId,
    facebook_page_id: credentials.facebookPageId,
    instagram_graph_version: credentials.instagramGraphVersion,
    threads_access_token: credentials.threadsAccessToken,
    threads_user_id:
      credentials.threadsUserId || credentials.instagramBusinessAccountId || "",
    naver_live_note: credentials.naverLiveNote,
  };
}

function buildCaptionForContent(contentType, spec) {
  if (contentType === "carousel") {
    return [
      spec.caption?.primary || "",
      spec.caption?.cta || "",
      Array.isArray(spec.hashtags) ? spec.hashtags.join(" ") : "",
    ]
      .filter(Boolean)
      .join("\n\n");
  }

  if (contentType === "video") {
    return [
      spec.textOverlays?.[0]?.text || "",
      ...(spec.voiceover?.scriptBlocks || []).map((entry) => entry.text || ""),
    ]
      .filter(Boolean)
      .join("\n");
  }

  if (contentType === "blog") {
    return [
      spec.title || "",
      ...(spec.sections || []).map((section) => section.body || ""),
      Array.isArray(spec.hashtags) ? spec.hashtags.join(" ") : "",
    ]
      .filter(Boolean)
      .join("\n\n");
  }

  if (contentType === "thread") {
    return buildThreadPublishText(spec);
  }

  return "";
}

function buildThreadPublishText(spec) {
  return [
    spec.mainPost || "",
    spec.reply1 || "",
    spec.reply2 || "",
    Array.isArray(spec.hashtags) ? spec.hashtags.join(" ") : "",
  ]
    .filter(Boolean)
    .join("\n\n");
}

function selectPreferredPhotoAssets(project, content, photoAssets) {
  if (content.contentType === "carousel") {
    const slideMediaIds = Array.isArray(content.spec?.slides)
      ? content.spec.slides.map((slide) => slide.mediaId).filter(Boolean)
      : [];
    const ordered = orderAssetsById(slideMediaIds, photoAssets);
    if (ordered.length > 0) {
      return ordered;
    }
  }

  if (content.contentType === "thread") {
    const attachedIds = Array.isArray(content.spec?.attachedMediaIds)
      ? content.spec.attachedMediaIds
      : [];
    const ordered = orderAssetsById(attachedIds, photoAssets);
    if (ordered.length > 0) {
      return ordered.slice(0, 4);
    }
  }

  const requested = Array.isArray(project.generationProfile?.photoPriority)
    ? project.generationProfile.photoPriority
    : [];
  const ordered = orderAssetsById(requested, photoAssets);
  if (ordered.length > 0) {
    return ordered;
  }

  return photoAssets;
}

function selectVideoPath(project, videoAssets) {
  const representativeId = project.generationProfile?.representativeMediaAssetId;
  const representativeVideo = videoAssets.find((asset) => asset.id === representativeId);
  return representativeVideo?.filePath || videoAssets[0]?.filePath || null;
}

function orderAssetsById(requestedIds, assets) {
  const assetMap = new Map(assets.map((asset) => [asset.id, asset]));
  const ordered = [];
  for (const mediaId of requestedIds || []) {
    const asset = assetMap.get(mediaId);
    if (asset && !ordered.find((entry) => entry.id === asset.id)) {
      ordered.push(asset);
    }
  }
  return ordered;
}

function getPublishArtifactPaths(projectFolderPath, contentType, executionMode, status) {
  const stamp = new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 17);
  return {
    latestPath: path.join(projectFolderPath, "published", `${contentType}_publish_result.json`),
    archivedPath: path.join(
      projectFolderPath,
      "published",
      "history",
      contentType,
      `${stamp}_${executionMode}_${status}.json`
    ),
  };
}

function writeManualHandoffArtifacts(
  projectFolderPath,
  contentType,
  executionMode,
  normalizedResult
) {
  if (executionMode !== "live" || normalizedResult.status !== "manual_ready") {
    return [];
  }

  const baseDir = path.join(projectFolderPath, "published", "manual", contentType);
  fs.mkdirSync(baseDir, { recursive: true });
  const written = [];

  if (contentType === "blog" && normalizedResult.manual_handoff?.markdown) {
    const markdownPath = path.join(baseDir, "naver_blog_manual.md");
    fs.writeFileSync(markdownPath, normalizedResult.manual_handoff.markdown, "utf8");
    written.push(markdownPath);
  }

  if (contentType === "video") {
    if (normalizedResult.manual_handoff?.caption) {
      const captionPath = path.join(baseDir, "instagram_reels_caption.txt");
      fs.writeFileSync(captionPath, normalizedResult.manual_handoff.caption, "utf8");
      written.push(captionPath);
    }
    const handoffJsonPath = path.join(baseDir, "instagram_reels_handoff.json");
    fs.writeFileSync(
      handoffJsonPath,
      JSON.stringify(normalizedResult.manual_handoff || {}, null, 2),
      "utf8"
    );
    written.push(handoffJsonPath);
  }

  return written;
}

function buildPublishItemSummary({ content, latestRun, credentialStatus }) {
  const config = getProviderConfig(content.contentType);
  if (config.supportTier === "manual_handoff") {
    return {
      contentType: content.contentType,
      platform: config.platform,
      supportTier: config.supportTier,
      liveStatus: "manual_ready",
      liveButtonLabel: "Create Manual Package",
      recommendedAction: config.recommendedAction,
      canRunLive: true,
      canRunLiveRecommended: true,
      latestRun,
      validationStatus: null,
      validationMessage: config.message,
    };
  }

  const providerStatus = config.providerKey
    ? getProviderStatus(config.providerKey, credentialStatus)
    : null;
  const validationStatus = String(providerStatus?.validation?.status || "");
  let liveStatus = "needs_validation";
  let validationMessage =
    providerStatus?.validation?.message || "Run provider validation before live publish.";
  let canRunLive = Boolean(providerStatus?.hasCredentials);
  let canRunLiveRecommended = false;
  let recommendedAction = "Validate provider";

  if (!providerStatus?.hasCredentials) {
    liveStatus = "blocked";
    validationMessage = config.missingMessage;
    canRunLive = false;
    recommendedAction = "Save credentials";
  } else if (validationStatus === "ok") {
    liveStatus = "ready";
    validationMessage = providerStatus.validation.message || "Provider is ready for live publish.";
    canRunLive = true;
    canRunLiveRecommended = true;
    recommendedAction = "Run live publish";
  } else if (validationStatus === "error") {
    liveStatus = "attention";
    validationMessage =
      providerStatus.validation.message || "Provider returned an error on the last validation.";
    canRunLive = true;
    recommendedAction = "Review credentials and retry";
  } else if (validationStatus === "missing") {
    liveStatus = "blocked";
    validationMessage =
      providerStatus.validation.message || config.missingMessage;
    canRunLive = false;
    recommendedAction = "Complete credentials";
  }

  return {
    contentType: content.contentType,
    platform: config.platform,
    supportTier: config.supportTier,
    liveStatus,
    liveButtonLabel: "Live Publish",
    recommendedAction,
    canRunLive,
    canRunLiveRecommended,
    latestRun,
    validationStatus: validationStatus || null,
    validationMessage,
  };
}

function getProviderConfig(contentType) {
  if (contentType === "blog") {
    return {
      platform: "Naver Blog",
      supportTier: "manual_handoff",
      recommendedAction: "Create Naver handoff package",
      message: "Desktop phase 10 creates a manual Naver publishing package instead of a direct live post.",
    };
  }
  if (contentType === "carousel") {
    return {
      platform: "Instagram Carousel",
      supportTier: "live_api",
      providerKey: "instagram",
      missingMessage: "Instagram live publish needs a token, Instagram business account id, and Facebook page id.",
    };
  }
  if (contentType === "video") {
    return {
      platform: "Instagram Reels",
      supportTier: "manual_handoff",
      recommendedAction: "Create Reels handoff package",
      message: "Desktop phase 10 creates a manual Reels handoff package instead of a direct live upload.",
    };
  }
  return {
    platform: "Threads",
    supportTier: "live_api",
    providerKey: "threads",
    missingMessage: "Threads live publish needs a token, Threads user id, and Facebook page id.",
  };
}

function getProviderStatus(providerKey, credentialStatus) {
  if (providerKey === "instagram") {
    return {
      hasCredentials:
        credentialStatus.instagram.accessTokenPresent &&
        Boolean(credentialStatus.instagram.instagramBusinessAccountId) &&
        Boolean(credentialStatus.instagram.facebookPageId),
      validation: credentialStatus.validation.instagram,
    };
  }
  if (providerKey === "threads") {
    return {
      hasCredentials:
        credentialStatus.threads.accessTokenPresent &&
        Boolean(credentialStatus.threads.threadsUserId) &&
        Boolean(credentialStatus.threads.facebookPageId),
      validation: credentialStatus.validation.threads,
    };
  }
  return {
    hasCredentials: false,
    validation: null,
  };
}

function normalizeExecutionMode(value) {
  return value === "live" ? "live" : "mock";
}

function normalizePublishStatus(value) {
  const candidate = String(value || "error").trim().toLowerCase();
  return candidate || "error";
}

function resolveContentStatus(currentStatus, publishStatus) {
  if (publishStatus === "published") {
    return "published";
  }
  if (String(currentStatus) === "published") {
    return "published";
  }
  return "ready";
}

module.exports = {
  PublishService,
  buildPublishPayload,
  buildPublishItemSummary,
};
