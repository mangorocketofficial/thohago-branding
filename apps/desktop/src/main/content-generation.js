const fs = require("node:fs");
const path = require("node:path");
const { randomUUID } = require("node:crypto");

class ContentGenerationService {
  constructor({ database, projectService, sidecarManager }) {
    this.database = database;
    this.projectService = projectService;
    this.sidecarManager = sidecarManager;
  }

  async generateAll(projectId) {
    const project = this.projectService.getProject(projectId);
    ensureProjectReadyToGenerate(project);

    const bundle = buildContentBundle(project);
    const generatedDir = path.join(project.projectFolderPath, "generated");
    writeJson(path.join(generatedDir, "content_bundle.json"), bundle);

    const [blog, carousel, video, thread] = await Promise.all([
      this.sidecarManager.call("content.compose_blog", { bundle }),
      this.sidecarManager.call("content.generate_carousel_spec", { bundle }),
      this.sidecarManager.call("content.generate_video_spec", { bundle }),
      this.sidecarManager.call("content.generate_thread", { bundle }),
    ]);

    this.persistContentOutput(project, "blog", blog, "initial", { mode: "initial" });
    this.persistContentOutput(project, "carousel", carousel, "initial", {
      mode: "initial",
    });
    this.persistContentOutput(project, "video", video, "initial", { mode: "initial" });
    this.persistContentOutput(project, "thread", thread, "initial", { mode: "initial" });

    this.database.run(
      "UPDATE projects SET status = ?, updated_at = ? WHERE id = ?",
      ["content_generated", new Date().toISOString(), projectId]
    );

    return this.projectService.getProject(projectId);
  }

  async regenerateContent(projectId, contentType, mode) {
    const project = this.projectService.getProject(projectId);
    const current = this.getContentSpec(projectId, contentType);
    if (!current) {
      throw new Error(`generate ${contentType} before regenerating it`);
    }

    const directive = buildRegenerationDirective(project, mode, contentType);
    const bundle = buildContentBundle(project);
    const method = {
      blog: "content.regenerate_blog",
      carousel: "content.regenerate_carousel",
      video: "content.regenerate_video",
      thread: "content.regenerate_thread",
    }[contentType];

    if (!method) {
      throw new Error(`unsupported content type: ${contentType}`);
    }

    const spec = await this.sidecarManager.call(method, {
      bundle,
      current_spec: current.spec,
      regeneration_directive: directive,
    });

    this.persistContentOutput(project, contentType, spec, mode, directive);

    this.database.run(
      "UPDATE projects SET status = ?, updated_at = ? WHERE id = ?",
      ["content_generated", new Date().toISOString(), projectId]
    );

    return this.projectService.getProject(projectId);
  }

  getContentSpec(projectId, contentType) {
    const row = this.database.get(
      `
      SELECT *
      FROM content_specs
      WHERE project_id = ? AND content_type = ?
      `,
      [projectId, contentType]
    );
    return row ? formatContentSpecRow(row) : null;
  }

  listContentSpecs(projectId) {
    return this.database
      .all(
        `
        SELECT *
        FROM content_specs
        WHERE project_id = ?
        ORDER BY content_type ASC
        `,
        [projectId]
      )
      .map(formatContentSpecRow);
  }

  getPreviewHtml(projectId, contentType) {
    const content = this.getContentSpec(projectId, contentType);
    if (!content || !content.previewArtifactPath) {
      return null;
    }
    return {
      previewArtifactPath: content.previewArtifactPath,
      html: fs.readFileSync(content.previewArtifactPath, "utf8"),
    };
  }

  getGenerationRuns(projectId, contentType) {
    return this.database
      .all(
        `
        SELECT
          r.*
        FROM generation_runs r
        JOIN content_specs c ON c.id = r.content_spec_id
        WHERE c.project_id = ? AND c.content_type = ?
        ORDER BY r.created_at DESC
        `,
        [projectId, contentType]
      )
      .map(formatGenerationRunRow);
  }

  persistContentOutput(project, contentType, spec, mode, directive) {
    const latestArtifacts = getLatestArtifactPaths(project.projectFolderPath, contentType);
    const previewHtml = buildPreviewHtmlForType(contentType, spec, buildContentBundle(project));

    writeJson(latestArtifacts.specPath, spec);
    fs.mkdirSync(path.dirname(latestArtifacts.previewPath), { recursive: true });
    fs.writeFileSync(latestArtifacts.previewPath, previewHtml, "utf8");

    const archivedArtifacts = getArchivedArtifactPaths(
      project.projectFolderPath,
      contentType,
      mode
    );
    writeJson(archivedArtifacts.specPath, spec);
    fs.writeFileSync(archivedArtifacts.previewPath, previewHtml, "utf8");

    const contentSpecId = this.upsertContentSpec(
      project.id,
      contentType,
      spec,
      latestArtifacts.specPath,
      latestArtifacts.previewPath
    );
    this.recordGenerationRun(
      contentSpecId,
      mode,
      directive,
      spec,
      archivedArtifacts.specPath,
      archivedArtifacts.previewPath
    );
  }

  upsertContentSpec(projectId, contentType, spec, artifactPath, previewArtifactPath) {
    const existing = this.database.get(
      "SELECT id FROM content_specs WHERE project_id = ? AND content_type = ?",
      [projectId, contentType]
    );
    const id = existing?.id || randomUUID();
    const now = new Date().toISOString();

    this.database.run(
      `
      INSERT INTO content_specs (
        id,
        project_id,
        content_type,
        spec_json,
        artifact_path,
        preview_artifact_path,
        status,
        created_at,
        updated_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
      ON CONFLICT(project_id, content_type) DO UPDATE SET
        spec_json = excluded.spec_json,
        artifact_path = excluded.artifact_path,
        preview_artifact_path = excluded.preview_artifact_path,
        status = excluded.status,
        updated_at = excluded.updated_at
      `,
      [
        id,
        projectId,
        contentType,
        JSON.stringify(spec),
        artifactPath,
        previewArtifactPath,
        "ready",
        now,
        now,
      ]
    );
    return id;
  }

  recordGenerationRun(
    contentSpecId,
    mode,
    directive,
    spec,
    artifactPath,
    previewArtifactPath
  ) {
    this.database.run(
      `
      INSERT INTO generation_runs (
        id,
        content_spec_id,
        mode,
        directive_json,
        spec_json,
        artifact_path,
        preview_artifact_path,
        created_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
      `,
      [
        randomUUID(),
        contentSpecId,
        mode,
        JSON.stringify(directive),
        JSON.stringify(spec),
        artifactPath,
        previewArtifactPath,
        new Date().toISOString(),
      ]
    );
  }
}

function ensureProjectReadyToGenerate(project) {
  if (
    project.status !== "ready_to_generate" &&
    project.status !== "content_generated" &&
    !project.generationProfile
  ) {
    throw new Error("save generation setup before generating content");
  }
  if (!project.generationProfile) {
    throw new Error("generation profile is missing");
  }
  const interviewStatus = project.latestInterview?.status ?? project.latestInterviewStatus;
  if (interviewStatus !== "completed") {
    throw new Error("complete the interview before generating content");
  }
}

function buildContentBundle(project) {
  return {
    projectId: project.id,
    projectName: project.name,
    shopDisplayName: project.shopDisplayName,
    summary: project.summary,
    status: project.status,
    generationProfile: project.generationProfile,
    preflight: project.preflight,
    interview: {
      turn1Question: project.latestInterview?.turn1Question ?? null,
      turn1Answer: project.latestInterview?.turn1Answer ?? null,
      turn2Question: project.latestInterview?.turn2Question ?? null,
      turn2Answer: project.latestInterview?.turn2Answer ?? null,
      turn3Question: project.latestInterview?.turn3Question ?? null,
      turn3Answer: project.latestInterview?.turn3Answer ?? null,
    },
    mediaAssets: project.mediaAssets.map((asset) => ({
      id: asset.id,
      kind: asset.kind,
      fileName: asset.fileName,
      filePath: asset.filePath,
      mimeType: asset.mimeType,
      experienceOrder: asset.experienceOrder,
      isHero: asset.isHero,
    })),
  };
}

function buildRegenerationDirective(project, mode, contentType) {
  return {
    mode,
    contentType,
    currentTone: project.generationProfile?.tone || "friendly",
    timestamp: new Date().toISOString(),
  };
}

function getLatestArtifactPaths(projectFolderPath, contentType) {
  const generatedDir = path.join(projectFolderPath, "generated");
  return {
    specPath: path.join(generatedDir, `${contentType}_spec.json`),
    previewPath: path.join(generatedDir, `${contentType}_preview.html`),
  };
}

function getArchivedArtifactPaths(projectFolderPath, contentType, mode) {
  const stamp = new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 17);
  const historyDir = path.join(projectFolderPath, "generated", "history", contentType);
  return {
    specPath: path.join(historyDir, `${stamp}_${mode}.json`),
    previewPath: path.join(historyDir, `${stamp}_${mode}.html`),
  };
}

function buildPreviewHtmlForType(contentType, spec, bundle) {
  if (contentType === "blog") {
    return buildBlogPreviewHtml(spec);
  }
  if (contentType === "carousel") {
    return buildCarouselPreviewHtml(spec, bundle);
  }
  if (contentType === "video") {
    return buildVideoPreviewHtml(spec);
  }
  if (contentType === "thread") {
    return buildThreadPreviewHtml(spec);
  }
  throw new Error(`unsupported preview content type: ${contentType}`);
}

function buildBlogPreviewHtml(spec) {
  const sections = (spec.sections || [])
    .map(
      (section) =>
        `<section><h2>${escapeHtml(section.heading || "")}</h2><p>${escapeHtml(
          section.body || ""
        )}</p></section>`
    )
    .join("");

  const hashtags = (spec.hashtags || []).map((tag) => escapeHtml(tag)).join(" ");
  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>${escapeHtml(spec.title || "블로그 미리보기")}</title>
    <style>
      body { font-family: 'Segoe UI', sans-serif; max-width: 760px; margin: 0 auto; padding: 32px; color: #2b1f1a; line-height: 1.7; }
      h1 { font-size: 2rem; margin-bottom: 0.5rem; }
      h2 { margin-top: 2rem; font-size: 1.2rem; }
      .hashtags { margin-top: 2rem; color: #9c6a3f; font-weight: 600; }
    </style>
  </head>
  <body>
    <h1>${escapeHtml(spec.title || "")}</h1>
    ${sections}
    <p class="hashtags">${hashtags}</p>
  </body>
</html>`;
}

function buildCarouselPreviewHtml(spec, bundle) {
  const slides = (spec.slides || [])
    .map((slide) => {
      const source = findMediaAsset(bundle, slide.mediaId);
      const imageTag = source
        ? `<img src="${dataUrlForMedia(source)}" alt="${escapeHtml(
            slide.fileName || slide.headline || "slide"
          )}" />`
        : `<div class="placeholder">이미지 없음</div>`;
      return `
        <article class="slide-card">
          ${imageTag}
          <div class="slide-copy">
            <h2>${escapeHtml(slide.headline || "")}</h2>
            <p>${escapeHtml(slide.subheadline || "")}</p>
          </div>
        </article>
      `;
    })
    .join("");

  return wrapPreviewHtml(
    "캐러셀 검토",
    `
      <section class="carousel-grid">${slides}</section>
      <footer class="meta">
        <strong>캡션</strong>
        <p>${escapeHtml(spec.caption?.primary || "")}</p>
        <p>${escapeHtml(spec.caption?.cta || "")}</p>
      </footer>
    `
  );
}

function buildVideoPreviewHtml(spec) {
  const timeline = (spec.timeline || [])
    .map(
      (clip) => `
        <article class="timeline-card">
          <h2>${escapeHtml(clip.clipId || "")}</h2>
          <p>${escapeHtml(clip.assetType || "")}</p>
          <p>${escapeHtml(String(clip.startSec || 0))}s - ${escapeHtml(
            String(clip.endSec || 0)
          )}s</p>
          <p>${escapeHtml(String(clip.sourcePath || ""))}</p>
        </article>
      `
    )
    .join("");

  const voiceover = (spec.voiceover?.scriptBlocks || [])
    .map((entry) => `<li>${escapeHtml(entry.text || "")}</li>`)
    .join("");

  return wrapPreviewHtml(
    "영상 검토",
    `
      <section class="timeline-grid">${timeline}</section>
      <section class="meta">
        <strong>보이스오버</strong>
        <ul>${voiceover}</ul>
      </section>
    `
  );
}

function buildThreadPreviewHtml(spec) {
  return wrapPreviewHtml(
    "스레드 검토",
    `
      <section class="thread-stack">
        <article class="thread-card main">${escapeHtml(spec.mainPost || "")}</article>
        <article class="thread-card reply">${escapeHtml(spec.reply1 || "")}</article>
        <article class="thread-card main">${escapeHtml(spec.reply2 || "")}</article>
      </section>
    `
  );
}

function wrapPreviewHtml(title, body) {
  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>${escapeHtml(title)}</title>
    <style>
      body { font-family: 'Segoe UI', sans-serif; margin: 0; padding: 28px; background: #f5efe7; color: #2b1f1a; }
      .carousel-grid, .timeline-grid { display: grid; gap: 16px; }
      .slide-card, .timeline-card, .thread-card, .meta { background: #fffaf4; border-radius: 18px; padding: 16px; box-shadow: 0 10px 24px rgba(46, 26, 11, 0.08); }
      .slide-card img { width: 100%; max-height: 420px; object-fit: cover; border-radius: 12px; display: block; margin-bottom: 12px; }
      .slide-copy h2 { margin: 0 0 8px; font-size: 1.05rem; }
      .thread-stack { display: grid; gap: 12px; }
      .thread-card.main { border-left: 6px solid #c87a3f; }
      .thread-card.reply { border-left: 6px solid #7db099; }
      .placeholder { padding: 24px; border-radius: 12px; background: rgba(0,0,0,0.05); text-align: center; }
      ul { margin: 8px 0 0 18px; }
    </style>
  </head>
  <body>
    ${body}
  </body>
</html>`;
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function writeJson(filePath, payload) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, JSON.stringify(payload, null, 2), "utf8");
}

function formatContentSpecRow(row) {
  return {
    id: row.id,
    projectId: row.project_id,
    contentType: row.content_type,
    spec: JSON.parse(row.spec_json),
    artifactPath: row.artifact_path || null,
    previewArtifactPath: row.preview_artifact_path || null,
    status: row.status,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

function formatGenerationRunRow(row) {
  return {
    id: row.id,
    mode: row.mode,
    directive: JSON.parse(row.directive_json),
    spec: JSON.parse(row.spec_json),
    artifactPath: row.artifact_path || null,
    previewArtifactPath: row.preview_artifact_path || null,
    createdAt: row.created_at,
  };
}

function findMediaAsset(bundle, mediaId) {
  return (bundle.mediaAssets || []).find((asset) => asset.id === mediaId) || null;
}

function dataUrlForMedia(asset) {
  const buffer = fs.readFileSync(asset.filePath);
  const mimeType = asset.mimeType || "application/octet-stream";
  return `data:${mimeType};base64,${buffer.toString("base64")}`;
}

module.exports = {
  ContentGenerationService,
  buildContentBundle,
};
