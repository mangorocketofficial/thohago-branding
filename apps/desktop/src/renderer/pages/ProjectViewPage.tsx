import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  translateContentLength,
  translateContentType,
  translateInterviewStatus,
  translateProjectStatus,
  translateTone,
} from "../lib/korean";

function preflightSummary(preflight: MediaPreflight | null) {
  if (!preflight) {
    return "아직 preflight가 없습니다.";
  }
  return preflight.summary;
}

export function ProjectViewPage() {
  const navigate = useNavigate();
  const params = useParams();
  const projectId = params.projectId as string;
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadProject() {
    const nextProject = await window.thohago.projects.get(projectId);
    setProject(nextProject);
    return nextProject;
  }

  useEffect(() => {
    loadProject().catch((nextError) => {
      setError(nextError instanceof Error ? nextError.message : String(nextError));
    });
  }, [projectId]);

  useEffect(() => {
    if (!project) {
      return;
    }

    window.thohago.app.reportSnapshot({
      route: `/project/${project.id}`,
      onboardingCompleted: true,
      projectId: project.id,
      mediaCount: project.mediaAssets.length,
      generatedContentCount: project.generatedContentCount,
      publishedContentCount: project.publishedContentCount,
      interviewStatus: project.latestInterview?.status ?? project.latestInterviewStatus,
      projectStatus: project.status,
    });
  }, [project]);

  async function handleImportMedia() {
    setBusy(true);
    setError(null);
    try {
      const filePaths = await window.thohago.projects.selectMediaFiles();
      if (filePaths.length === 0) {
        setBusy(false);
        return;
      }
      const imported = await window.thohago.projects.importMedia({ projectId, filePaths });
      setProject(imported);
      const withPreflight = await window.thohago.projects.buildPreflight(projectId);
      setProject(withPreflight);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : String(nextError));
    } finally {
      setBusy(false);
    }
  }

  async function handleRefreshPreflight() {
    setBusy(true);
    setError(null);
    try {
      setProject(await window.thohago.projects.buildPreflight(projectId));
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : String(nextError));
    } finally {
      setBusy(false);
    }
  }

  async function handleSetHero(mediaAssetId: string) {
    setBusy(true);
    try {
      setProject(
        await window.thohago.projects.setHeroMedia({
          projectId,
          mediaAssetId,
        })
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleMove(assetId: string, direction: -1 | 1) {
    if (!project) {
      return;
    }

    const orderedIds = [...project.mediaAssets]
      .sort((left, right) => left.experienceOrder - right.experienceOrder)
      .map((asset) => asset.id);
    const index = orderedIds.indexOf(assetId);
    const targetIndex = index + direction;
    if (index < 0 || targetIndex < 0 || targetIndex >= orderedIds.length) {
      return;
    }

    const nextIds = [...orderedIds];
    [nextIds[index], nextIds[targetIndex]] = [nextIds[targetIndex], nextIds[index]];

    setBusy(true);
    try {
      setProject(
        await window.thohago.projects.updateMediaOrder({
          projectId,
          orderedAssetIds: nextIds,
        })
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleStartInterview() {
    setBusy(true);
    try {
      await window.thohago.interview.start(projectId);
      navigate(`/project/${projectId}/interview`);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : String(nextError));
    } finally {
      setBusy(false);
    }
  }

  async function handleGenerateAll() {
    setBusy(true);
    setError(null);
    try {
      const generated = await window.thohago.content.generateAll(projectId);
      setProject(generated);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : String(nextError));
    } finally {
      setBusy(false);
    }
  }

  if (!project) {
    return (
      <div className="loading-shell">
        <h1>프로젝트를 불러오는 중입니다...</h1>
      </div>
    );
  }

  return (
    <section className="page page-project">
      <div className="panel project-header">
        <div>
          <p className="eyebrow">프로젝트 상세</p>
          <h1>{project.shopDisplayName}</h1>
          <p className="lede">{project.summary || "아직 요약이 없습니다."}</p>
        </div>
        <div className="button-row">
          <Link className="ghost-button button-link" to="/">
            대시보드
          </Link>
          <button className="secondary-button" disabled={busy} onClick={handleImportMedia}>
            미디어 가져오기
          </button>
          <button className="ghost-button" disabled={busy} onClick={handleRefreshPreflight}>
            Preflight 새로고침
          </button>
          <button className="primary-button" disabled={busy} onClick={handleStartInterview}>
            {project.latestInterview && project.latestInterview.status !== "completed"
              ? "인터뷰 이어하기"
              : "인터뷰 시작"}
          </button>
          <Link
            className={
              project.latestInterview?.status === "completed"
                ? "secondary-button button-link"
                : "ghost-button button-link disabled-link"
            }
            to={
              project.latestInterview?.status === "completed"
                ? `/project/${projectId}/generate`
                : `/project/${projectId}`
            }
            onClick={(event) => {
              if (project.latestInterview?.status !== "completed") {
                event.preventDefault();
              }
            }}
          >
            생성 설정
          </Link>
          <button
            className={
              project.status === "ready_to_generate"
                ? "primary-button"
                : "ghost-button"
            }
            disabled={busy || project.status !== "ready_to_generate"}
            onClick={handleGenerateAll}
          >
            전체 콘텐츠 생성
          </button>
          <Link
            className={
              project.generatedContentCount === 4
                ? "secondary-button button-link"
                : "ghost-button button-link disabled-link"
            }
            to={
              project.generatedContentCount === 4
                ? `/project/${projectId}/publish`
                : `/project/${projectId}`
            }
            onClick={(event) => {
              if (project.generatedContentCount !== 4) {
                event.preventDefault();
              }
            }}
          >
            발행
          </Link>
        </div>
      </div>

      {error ? <p className="error-banner">{error}</p> : null}

      <div className="project-grid">
        <article className="panel">
          <h2>프로젝트 상태</h2>
          <dl className="detail-list compact">
            <div>
              <dt>상태</dt>
              <dd>{translateProjectStatus(project.status)}</dd>
            </div>
            <div>
              <dt>프로젝트 폴더</dt>
              <dd>{project.projectFolderPath}</dd>
            </div>
            <div>
              <dt>미디어 폴더</dt>
              <dd>{project.mediaFolderPath}</dd>
            </div>
            <div>
              <dt>최근 인터뷰</dt>
              <dd>{translateInterviewStatus(project.latestInterview?.status)}</dd>
            </div>
            <div>
              <dt>발행된 콘텐츠</dt>
              <dd>{project.publishedContentCount}/4</dd>
            </div>
          </dl>
        </article>

        <article className="panel">
          <h2>미디어 Preflight</h2>
          <p>{preflightSummary(project.preflight)}</p>
          <ul className="notes-list">
            {(project.preflight?.notes || []).map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </article>

        <article className="panel">
          <h2>생성 설정</h2>
          {project.generationProfile ? (
            <>
              <p>
                상태: <strong>{translateProjectStatus(project.status)}</strong>
              </p>
              <ul className="notes-list">
                <li>업종: {project.generationProfile.industry || "설정되지 않음"}</li>
                <li>톤: {translateTone(project.generationProfile.tone)}</li>
                <li>길이: {translateContentLength(project.generationProfile.contentLength)}</li>
                <li>
                  대표 미디어:{" "}
                  {project.generationProfile.representativeMediaAssetId ?? "설정되지 않음"}
                </li>
              </ul>
            </>
          ) : (
            <p>
              인터뷰를 마친 뒤 구조화된 생성 프로필을 저장하면 이 프로젝트를 생성 가능 상태로 전환할 수 있습니다.
            </p>
          )}
        </article>
      </div>

      <article className="panel">
        <h2>생성된 콘텐츠</h2>
        {project.contentSpecs.length === 0 ? (
          <div className="empty-state">
            <strong>아직 생성된 콘텐츠가 없습니다.</strong>
            <p>생성 설정을 저장한 뒤 "전체 콘텐츠 생성"을 실행하세요.</p>
          </div>
        ) : (
          <div className="project-list">
            {project.contentSpecs.map((entry) => (
              <Link
                key={entry.contentType}
                className="project-card"
                to={`/project/${projectId}/${entry.contentType}`}
              >
                <div className="project-card-top">
                  <strong>{translateContentType(entry.contentType)}</strong>
                  <span className="status-pill">{translateProjectStatus(entry.status)}</span>
                </div>
                <p>{entry.artifactPath ?? "아직 아티팩트 경로가 기록되지 않았습니다."}</p>
              </Link>
            ))}
          </div>
        )}
      </article>

      <article className="panel">
        <h2>가져온 미디어</h2>
        {project.mediaAssets.length === 0 ? (
          <div className="empty-state">
            <strong>아직 미디어가 없습니다.</strong>
            <p>사진을 하나 이상 가져오면 preflight와 인터뷰를 시작할 수 있습니다.</p>
          </div>
        ) : (
          <div className="media-list">
            {project.mediaAssets.map((asset, index) => (
              <div key={asset.id} className={`media-card ${asset.isHero ? "hero-media" : ""}`}>
                <div className="media-card-top">
                  <strong>{asset.fileName}</strong>
                  <span>{asset.kind}</span>
                </div>
                <p>{asset.filePath}</p>
                <div className="button-row">
                  <button
                    className="ghost-button"
                    disabled={busy || index === 0}
                    onClick={() => handleMove(asset.id, -1)}
                  >
                    위로 이동
                  </button>
                  <button
                    className="ghost-button"
                    disabled={busy || index === project.mediaAssets.length - 1}
                    onClick={() => handleMove(asset.id, 1)}
                  >
                    아래로 이동
                  </button>
                  <button
                    className={asset.isHero ? "secondary-button" : "ghost-button"}
                    disabled={busy}
                    onClick={() => handleSetHero(asset.id)}
                  >
                    {asset.isHero ? "대표 미디어" : "대표로 설정"}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </article>
    </section>
  );
}
