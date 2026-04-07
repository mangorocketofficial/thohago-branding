import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  translateContentType,
  translateContentTypeTitle,
  translateGenerationMode,
} from "../lib/korean";

type Props = {
  contentType: "blog" | "carousel" | "video" | "thread";
};

function titleFor(contentType: Props["contentType"]) {
  return translateContentTypeTitle(contentType);
}

export function ContentReviewPage({ contentType }: Props) {
  const params = useParams();
  const projectId = params.projectId as string;
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [spec, setSpec] = useState<ContentSpec | null>(null);
  const [preview, setPreview] = useState<{ previewArtifactPath: string; html: string } | null>(
    null
  );
  const [runs, setRuns] = useState<GenerationRun[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadReviewState() {
    const [projectDetail, contentSpec, previewHtml, generationRuns] = await Promise.all([
      window.thohago.projects.get(projectId),
      window.thohago.content.getSpec(projectId, contentType),
      window.thohago.content.getPreviewHtml(projectId, contentType),
      window.thohago.content.getRuns(projectId, contentType),
    ]);
    setProject(projectDetail);
    setSpec(contentSpec);
    setPreview(previewHtml);
    setRuns(generationRuns);
  }

  useEffect(() => {
    loadReviewState().catch((nextError) => {
      setError(nextError instanceof Error ? nextError.message : String(nextError));
    });
  }, [contentType, projectId]);

  useEffect(() => {
    if (!project || !spec) {
      return;
    }

    window.thohago.app.reportSnapshot({
      route: `/project/${projectId}/${contentType}`,
      onboardingCompleted: true,
      projectId,
      contentType,
      projectStatus: project.status,
      generatedContentCount: project.generatedContentCount,
      generationRunCount: runs.length,
      regenerationMode: runs[0]?.mode ?? null,
    });
  }, [contentType, project, projectId, runs.length, spec]);

  async function handleRegenerate(
    mode:
      | "regenerate"
      | "tone_shift"
      | "length_shorter"
      | "length_longer"
      | "premium"
      | "cta_boost"
  ) {
    setBusy(true);
    setError(null);
    try {
      await window.thohago.content.regenerate({
        projectId,
        contentType,
        mode,
      });
      await loadReviewState();
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : String(nextError));
    } finally {
      setBusy(false);
    }
  }

  if (error) {
    return (
      <div className="loading-shell">
        <h1>검토 화면을 불러오지 못했습니다</h1>
        <p>{error}</p>
      </div>
    );
  }

  if (!project || !spec) {
    return (
      <div className="loading-shell">
        <h1>생성된 콘텐츠를 불러오는 중입니다...</h1>
      </div>
    );
  }

  return (
    <section className="page page-project">
      <div className="panel project-header">
        <div>
          <p className="eyebrow">{titleFor(contentType)}</p>
          <h1>{project.shopDisplayName}</h1>
          <p className="lede">{translateContentType(contentType)} 결과물을 미리보기 중심으로 검토합니다.</p>
        </div>
        <div className="button-row">
          <Link className="ghost-button button-link" to={`/project/${projectId}`}>
            프로젝트로 돌아가기
          </Link>
        </div>
      </div>

      {preview ? (
        <article className="panel">
          <h2>렌더된 미리보기</h2>
          <p className="artifact-path">{preview.previewArtifactPath}</p>
          <iframe
            className="preview-frame"
            sandbox=""
            srcDoc={preview.html}
            title={`${contentType}-preview`}
          />
        </article>
      ) : null}

      <article className="panel">
        <h2>재생성 액션</h2>
        <div className="button-row">
          <button className="secondary-button" disabled={busy} onClick={() => handleRegenerate("regenerate")}>
            다시 생성
          </button>
          <button className="ghost-button" disabled={busy} onClick={() => handleRegenerate("tone_shift")}>
            톤 변경
          </button>
          <button className="ghost-button" disabled={busy} onClick={() => handleRegenerate("length_shorter")}>
            짧게
          </button>
          <button className="ghost-button" disabled={busy} onClick={() => handleRegenerate("length_longer")}>
            길게
          </button>
          <button className="ghost-button" disabled={busy} onClick={() => handleRegenerate("premium")}>
            더 프리미엄하게
          </button>
          <button className="ghost-button" disabled={busy} onClick={() => handleRegenerate("cta_boost")}>
            CTA 강화
          </button>
        </div>
        {busy ? <p className="info-banner">제한된 재생성 액션을 적용 중입니다...</p> : null}
      </article>

      <article className="panel">
        <h2>저장된 아티팩트 경로</h2>
        <dl className="detail-list compact">
          <div>
            <dt>스펙 아티팩트</dt>
            <dd>{spec.artifactPath ?? "기록되지 않음"}</dd>
          </div>
          <div>
            <dt>미리보기 아티팩트</dt>
            <dd>{spec.previewArtifactPath ?? "기록되지 않음"}</dd>
          </div>
        </dl>
      </article>

      <article className="panel">
        <h2>실행 이력</h2>
        <div className="project-list">
          {runs.map((run) => (
            <div key={run.id} className="project-card">
              <div className="project-card-top">
                <strong>{translateGenerationMode(run.mode)}</strong>
                <span className="status-pill">{run.createdAt}</span>
              </div>
              <p>{run.previewArtifactPath ?? "미리보기 아티팩트가 없습니다."}</p>
            </div>
          ))}
        </div>
      </article>

      <article className="panel">
        <h2>스펙 요약</h2>
        <pre className="spec-json">{JSON.stringify(spec.spec, null, 2)}</pre>
      </article>
    </section>
  );
}
