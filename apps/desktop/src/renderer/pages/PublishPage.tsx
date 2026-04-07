import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  translateContentType,
  translateExecutionMode,
  translateLiveStatus,
  translateProviderMessage,
  translatePublishStatus,
  translateSupportTier,
} from "../lib/korean";

const ITEMS: Array<{
  contentType: "blog" | "carousel" | "video" | "thread";
  platform: string;
}> = [
  { contentType: "blog", platform: "Naver Blog" },
  { contentType: "carousel", platform: "Instagram Carousel" },
  { contentType: "video", platform: "Instagram Reels" },
  { contentType: "thread", platform: "Threads" },
];

function validationLabel(result: Record<string, unknown> | null | undefined) {
  if (!result) {
    return "미확인";
  }
  return translatePublishStatus(String(result.status || "unknown"));
}

function validationMessage(result: Record<string, unknown> | null | undefined) {
  if (!result) {
    return "아직 라이브 검증 기록이 없습니다.";
  }
  return translateProviderMessage(String(result.message || "No provider message returned."));
}

export function PublishPage() {
  const params = useParams();
  const projectId = params.projectId as string;
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [publishRuns, setPublishRuns] = useState<PublishRun[]>([]);
  const [publishSummary, setPublishSummary] = useState<PublishSummary | null>(null);
  const [credentialStatus, setCredentialStatus] = useState<PublishCredentialStatus | null>(null);
  const [credentials, setCredentials] = useState({
    graphMetaAccessToken: "",
    instagramBusinessAccountId: "",
    facebookPageId: "",
    instagramGraphVersion: "v23.0",
    threadsAccessToken: "",
    threadsUserId: "",
    naverLiveNote: "",
  });
  const [busyContentType, setBusyContentType] = useState<string | null>(null);
  const [busyValidation, setBusyValidation] = useState<string | null>(null);
  const [busyBulkAction, setBusyBulkAction] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function loadState() {
    const [projectDetail, runs, status, summary] = await Promise.all([
      window.thohago.projects.get(projectId),
      window.thohago.publish.getRuns(projectId),
      window.thohago.publish.getCredentialStatus(),
      window.thohago.publish.getSummary(projectId),
    ]);
    setProject(projectDetail);
    setPublishRuns(runs);
    setCredentialStatus(status);
    setPublishSummary(summary);
    setCredentials((current) => ({
      ...current,
      instagramBusinessAccountId: status.instagram.instagramBusinessAccountId || "",
      facebookPageId: status.instagram.facebookPageId || "",
      instagramGraphVersion: status.instagram.instagramGraphVersion || "v23.0",
      threadsUserId: status.threads.threadsUserId || "",
      naverLiveNote: status.naver.naverLiveNote || "",
    }));
  }

  useEffect(() => {
    loadState().catch((nextError) => {
      setError(nextError instanceof Error ? nextError.message : String(nextError));
    });
  }, [projectId]);

  useEffect(() => {
    if (!project || !credentialStatus || !publishSummary) {
      return;
    }
    const latestPublishStatuses = ITEMS.reduce<Record<string, string | null>>((acc, item) => {
      acc[item.contentType] = latestRunFor(item.contentType)?.status ?? null;
      return acc;
    }, {});
    const latestPublishModes = ITEMS.reduce<Record<string, string | null>>((acc, item) => {
      acc[item.contentType] = latestRunFor(item.contentType)?.executionMode ?? null;
      return acc;
    }, {});
    window.thohago.app.reportSnapshot({
      route: `/project/${projectId}/publish`,
      onboardingCompleted: true,
      projectId,
      projectStatus: project.status,
      publishedContentCount: project.publishedContentCount,
      instagramCredentialPresent: credentialStatus.instagram.accessTokenPresent,
      threadsCredentialPresent: credentialStatus.threads.accessTokenPresent,
      instagramValidation: credentialStatus?.validation.instagram?.status ?? null,
      threadsValidation: credentialStatus?.validation.threads?.status ?? null,
      naverValidation: credentialStatus?.validation.naver?.status ?? null,
      publishRunCount: publishRuns.length,
      latestPublishStatuses,
      latestPublishModes,
      publishSummaryCounts: publishSummary.counts,
    });
  }, [credentialStatus, project, projectId, publishRuns, publishSummary]);

  async function handlePublish(
    contentType: "blog" | "carousel" | "video" | "thread",
    executionMode: "mock" | "live"
  ) {
    setBusyContentType(`${contentType}:${executionMode}`);
    setError(null);
    try {
      const updated = await window.thohago.publish.run({
        projectId,
        contentType,
        executionMode,
      });
      setProject(updated);
      await loadState();
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : String(nextError));
    } finally {
      setBusyContentType(null);
    }
  }

  async function handleSaveCredentials() {
    setBusyValidation("save");
    setError(null);
    try {
      setCredentialStatus(await window.thohago.publish.saveCredentials(credentials));
      setPublishSummary(await window.thohago.publish.getSummary(projectId));
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : String(nextError));
    } finally {
      setBusyValidation(null);
    }
  }

  async function handleValidate(provider: "instagram" | "threads" | "naver") {
    setBusyValidation(provider);
    setError(null);
    try {
      setCredentialStatus(await window.thohago.publish.validateProvider(provider));
      setPublishSummary(await window.thohago.publish.getSummary(projectId));
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : String(nextError));
    } finally {
      setBusyValidation(null);
    }
  }

  async function handleValidateAll() {
    setBusyBulkAction("validate-all");
    setError(null);
    try {
      let latestStatus = credentialStatus;
      latestStatus = await window.thohago.publish.validateProvider("instagram");
      latestStatus = await window.thohago.publish.validateProvider("threads");
      latestStatus = await window.thohago.publish.validateProvider("naver");
      setCredentialStatus(latestStatus);
      setPublishSummary(await window.thohago.publish.getSummary(projectId));
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : String(nextError));
    } finally {
      setBusyBulkAction(null);
    }
  }

  async function handleRunRecommended() {
    setBusyBulkAction("run-recommended");
    setError(null);
    try {
      const result = await window.thohago.publish.runRecommended(projectId);
      setProject(result.project);
      setPublishSummary(result.summary);
      setPublishRuns(await window.thohago.publish.getRuns(projectId));
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : String(nextError));
    } finally {
      setBusyBulkAction(null);
    }
  }

  function latestRunFor(contentType: string) {
    return publishRuns.find((run) => run.contentType === contentType) ?? null;
  }

  function summaryFor(contentType: "blog" | "carousel" | "video" | "thread") {
    return publishSummary?.items.find((item) => item.contentType === contentType) ?? null;
  }

  if (!project || !credentialStatus || !publishSummary) {
    return (
      <div className="loading-shell">
        <h1>발행 상태를 불러오는 중입니다...</h1>
      </div>
    );
  }

  return (
    <section className="page page-project">
      <div className="panel project-header">
        <div>
          <p className="eyebrow">발행</p>
          <h1>{project.shopDisplayName}</h1>
          <p className="lede">
            모의 발행과 라이브 발행을 같은 화면에서 관리할 수 있습니다. 라이브 실행 결과와 실패 상태도 모두 기록됩니다.
          </p>
        </div>
        <div className="button-row">
          <Link className="ghost-button button-link" to={`/project/${projectId}`}>
            프로젝트로 돌아가기
          </Link>
        </div>
      </div>

      {error ? <p className="error-banner">{error}</p> : null}

      <article className="panel">
        <h2>발행 요약</h2>
        <div className="project-grid">
          <div className="project-card">
            <div className="project-card-top">
              <strong>지원 현황</strong>
              <span className="status-pill">{publishSummary.counts.total}</span>
            </div>
            <p>수동 패키지 준비: {publishSummary.counts.manualReady}</p>
            <p>라이브 발행 가능: {publishSummary.counts.liveReady}</p>
            <p>차단됨: {publishSummary.counts.blocked}</p>
            <p>확인 필요: {publishSummary.counts.attention}</p>
          </div>
          <div className="project-card">
            <div className="project-card-top">
              <strong>일괄 작업</strong>
              <span className="status-pill">{publishRuns.length}회 실행</span>
            </div>
            <p>먼저 전체 검증을 실행한 뒤, 이 화면에서 권장 발행 대상을 한 번에 처리하세요.</p>
            <div className="button-row">
              <button
                className="secondary-button"
                disabled={busyBulkAction === "validate-all"}
                onClick={handleValidateAll}
              >
                {busyBulkAction === "validate-all" ? "검증 중..." : "전체 프로바이더 검증"}
              </button>
              <button
                className="primary-button"
                disabled={busyBulkAction === "run-recommended"}
                onClick={handleRunRecommended}
              >
                {busyBulkAction === "run-recommended" ? "실행 중..." : "권장 발행 실행"}
              </button>
            </div>
          </div>
        </div>
      </article>

      <article className="panel">
        <h2>라이브 자격 증명</h2>
        <div className="project-grid">
          <div className="stack-form">
            <label>
              Meta 액세스 토큰
              <input
                type="password"
                value={credentials.graphMetaAccessToken}
                onChange={(event) =>
                  setCredentials({ ...credentials, graphMetaAccessToken: event.target.value })
                }
                placeholder={
                  credentialStatus.instagram.accessTokenPresent ? "저장됨" : "변경할 때만 입력"
                }
              />
            </label>
            <label>
              인스타그램 비즈니스 계정 ID
              <input
                value={credentials.instagramBusinessAccountId}
                onChange={(event) =>
                  setCredentials({
                    ...credentials,
                    instagramBusinessAccountId: event.target.value,
                  })
                }
              />
            </label>
            <label>
              Facebook 페이지 ID
              <input
                value={credentials.facebookPageId}
                onChange={(event) =>
                  setCredentials({ ...credentials, facebookPageId: event.target.value })
                }
              />
            </label>
            <label>
              Graph 버전
              <input
                value={credentials.instagramGraphVersion}
                onChange={(event) =>
                  setCredentials({
                    ...credentials,
                    instagramGraphVersion: event.target.value,
                  })
                }
              />
            </label>
            <label>
              Threads 액세스 토큰
              <input
                type="password"
                value={credentials.threadsAccessToken}
                onChange={(event) =>
                  setCredentials({ ...credentials, threadsAccessToken: event.target.value })
                }
                placeholder={
                  credentialStatus.threads.accessTokenPresent ? "저장됨" : "변경할 때만 입력"
                }
              />
            </label>
            <label>
              Threads 사용자 ID
              <input
                value={credentials.threadsUserId}
                onChange={(event) =>
                  setCredentials({ ...credentials, threadsUserId: event.target.value })
                }
              />
            </label>
            <label>
              네이버 라이브 메모
              <input
                value={credentials.naverLiveNote}
                onChange={(event) =>
                  setCredentials({ ...credentials, naverLiveNote: event.target.value })
                }
                placeholder="네이버 직접 발행에 필요한 쿠키나 메모를 기록하세요"
              />
            </label>
            <div className="button-row">
              <button className="primary-button" disabled={busyValidation === "save"} onClick={handleSaveCredentials}>
                {busyValidation === "save" ? "저장 중..." : "자격 증명 저장"}
              </button>
            </div>
          </div>

          <div className="stack-form">
            <div className="project-card">
              <div className="project-card-top">
                <strong>인스타그램 라이브 검증</strong>
                <span className="status-pill">
                  {validationLabel(credentialStatus.validation.instagram)}
                </span>
              </div>
              <p>
                토큰 저장 여부: {credentialStatus.instagram.accessTokenPresent ? "예" : "아니오"}
              </p>
              <p>{validationMessage(credentialStatus.validation.instagram)}</p>
              <button
                className="secondary-button"
                disabled={busyValidation === "instagram"}
                onClick={() => handleValidate("instagram")}
              >
                {busyValidation === "instagram" ? "검증 중..." : "인스타그램 검증"}
              </button>
            </div>

            <div className="project-card">
              <div className="project-card-top">
                <strong>Threads 라이브 검증</strong>
                <span className="status-pill">
                  {validationLabel(credentialStatus.validation.threads)}
                </span>
              </div>
              <p>
                토큰 저장 여부: {credentialStatus.threads.accessTokenPresent ? "예" : "아니오"}
              </p>
              <p>{validationMessage(credentialStatus.validation.threads)}</p>
              <button
                className="secondary-button"
                disabled={busyValidation === "threads"}
                onClick={() => handleValidate("threads")}
              >
                {busyValidation === "threads" ? "검증 중..." : "Threads 검증"}
              </button>
            </div>

            <div className="project-card">
              <div className="project-card-top">
                <strong>네이버 라이브 상태</strong>
                <span className="status-pill">
                  {validationLabel(credentialStatus.validation.naver)}
                </span>
              </div>
              <p>{validationMessage(credentialStatus.validation.naver)}</p>
              <button
                className="secondary-button"
                disabled={busyValidation === "naver"}
                onClick={() => handleValidate("naver")}
              >
                {busyValidation === "naver" ? "확인 중..." : "네이버 확인"}
              </button>
            </div>
          </div>
        </div>
      </article>

      <div className="project-list">
        {ITEMS.map((item) => {
          const latest = latestRunFor(item.contentType);
          const summary = summaryFor(item.contentType);
          const content = project.contentSpecs.find(
            (entry) => entry.contentType === item.contentType
          );
          const canPublish = Boolean(content);
          return (
            <article key={item.contentType} className="project-card">
              <div className="project-card-top">
                <strong>{item.platform}</strong>
                <span className="status-pill">
                  {translatePublishStatus(latest?.status ?? content?.status ?? "ready")}
                </span>
              </div>
              <p>{translateContentType(item.contentType)}</p>
              <p>
                지원 방식: {translateSupportTier(summary?.supportTier ?? "unknown")}
                {" | "}
                라이브 상태: {translateLiveStatus(summary?.liveStatus ?? "unknown")}
              </p>
              <p>{latest?.permalink ?? "아직 퍼머링크가 없습니다."}</p>
              <p>
                최근 실행 모드: {translateExecutionMode(latest?.executionMode ?? "none")}
                {" | "}
                {translateProviderMessage(String(latest?.result?.message || "No provider message yet."))}
              </p>
              <p>{translateProviderMessage(summary?.validationMessage ?? "No summary available.")}</p>
              <p>권장 작업: {translateProviderMessage(summary?.recommendedAction ?? "Review manually")}</p>
              <div className="button-row">
                <button
                  className="primary-button"
                  disabled={!canPublish || busyContentType === `${item.contentType}:mock`}
                  onClick={() => handlePublish(item.contentType, "mock")}
                >
                  {busyContentType === `${item.contentType}:mock`
                    ? "발행 중..."
                    : "모의 발행"}
                </button>
                <button
                  className="secondary-button"
                  disabled={
                    !canPublish ||
                    !summary?.canRunLive ||
                    busyContentType === `${item.contentType}:live`
                  }
                  onClick={() => handlePublish(item.contentType, "live")}
                >
                  {busyContentType === `${item.contentType}:live`
                    ? "발행 중..."
                    : translateProviderMessage(summary?.liveButtonLabel || "Live Publish")}
                </button>
                {content ? (
                  <Link className="ghost-button button-link" to={`/project/${projectId}/${item.contentType}`}>
                    검토
                  </Link>
                ) : null}
              </div>
            </article>
          );
        })}
      </div>

      <article className="panel">
        <h2>발행 실행 이력</h2>
        <div className="project-list">
          {publishRuns.map((run) => (
            <div key={run.id} className="project-card">
              <div className="project-card-top">
                <strong>
                  {run.contentType}
                  {" -> "}
                  {run.platform}
                </strong>
                <span className="status-pill">{run.status}</span>
              </div>
              <p>{translateExecutionMode(run.executionMode)}</p>
              <p>{run.permalink ?? "퍼머링크 없음"}</p>
              <p>{translateProviderMessage(String(run.result.message || run.result.provider || "No provider detail"))}</p>
              <p>
                {Array.isArray(run.result.manualArtifactPaths) && run.result.manualArtifactPaths.length > 0
                  ? `수동 아티팩트 ${run.result.manualArtifactPaths.length}개`
                  : "수동 아티팩트 없음"}
              </p>
              <p>{run.artifactPath ?? "아티팩트 경로 없음"}</p>
            </div>
          ))}
        </div>
      </article>
    </section>
  );
}
