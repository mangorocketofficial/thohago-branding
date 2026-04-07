import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  translateInterviewStatus,
  translateProjectStatus,
} from "../lib/korean";

function listToText(items: string[]) {
  return items.join(", ");
}

export function GenerationSetupPage() {
  const navigate = useNavigate();
  const params = useParams();
  const projectId = params.projectId as string;
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [profile, setProfile] = useState<GenerationProfile | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadState() {
    const detail = await window.thohago.projects.get(projectId);
    const defaults = await window.thohago.projects.getGenerationDefaults(projectId);
    setProject(detail);
    setProfile(detail.generationProfile ?? defaults);
  }

  useEffect(() => {
    loadState().catch((nextError) => {
      setError(nextError instanceof Error ? nextError.message : String(nextError));
    });
  }, [projectId]);

  useEffect(() => {
    if (!project) {
      return;
    }
    window.thohago.app.reportSnapshot({
      route: `/project/${project.id}/generate`,
      onboardingCompleted: true,
      projectId: project.id,
      projectStatus: project.status,
      generationReady: project.status === "ready_to_generate",
      interviewStatus: project.latestInterview?.status ?? project.latestInterviewStatus,
    });
  }, [project]);

  const sortedMedia = useMemo(() => {
    if (!project) {
      return [];
    }

    return [...project.mediaAssets].sort(
      (left, right) => left.experienceOrder - right.experienceOrder
    );
  }, [project]);

  const canConfigure = project?.latestInterview?.status === "completed";

  async function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!profile) {
      return;
    }

    setBusy(true);
    setError(null);
    try {
      const saved = await window.thohago.projects.saveGenerationProfile({
        projectId,
        profile,
      });
      setProject(saved);
      setProfile(saved.generationProfile);
      navigate(`/project/${projectId}`, { replace: true });
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : String(nextError));
    } finally {
      setBusy(false);
    }
  }

  async function handleGenerateAll() {
    if (!profile) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await window.thohago.projects.saveGenerationProfile({
        projectId,
        profile,
      });
      const generated = await window.thohago.content.generateAll(projectId);
      setProject(generated);
      setProfile(generated.generationProfile);
      navigate(`/project/${projectId}`, { replace: true });
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : String(nextError));
    } finally {
      setBusy(false);
    }
  }

  function togglePriority(mediaId: string) {
    if (!profile) {
      return;
    }

    const rest = profile.photoPriority.filter((id) => id !== mediaId);
    setProfile({
      ...profile,
      photoPriority: [mediaId, ...rest],
    });
  }

  if (!project || !profile) {
    return (
      <div className="loading-shell">
        <h1>생성 설정을 불러오는 중입니다...</h1>
      </div>
    );
  }

  return (
    <section className="page page-form">
      <div className="panel hero-panel">
        <p className="eyebrow">생성 설정</p>
        <h1>{project.shopDisplayName}</h1>
        <p className="lede">
          이후 콘텐츠 생성 단계에서 사용할 구조화된 입력값을 저장하세요.
        </p>
        <div className="summary-grid">
          <article>
            <span>인터뷰</span>
            <strong>{translateInterviewStatus(project.latestInterview?.status)}</strong>
          </article>
          <article>
            <span>미디어</span>
            <strong>{project.mediaAssets.length}</strong>
          </article>
          <article>
            <span>상태</span>
            <strong>{translateProjectStatus(project.status)}</strong>
          </article>
          <article>
            <span>대표 미디어</span>
            <strong>{profile.representativeMediaAssetId ?? "설정되지 않음"}</strong>
          </article>
        </div>
      </div>

      <div className="panel flow-panel">
        {!canConfigure ? (
          <div className="stack-form">
            <h2>생성 설정이 잠겨 있습니다</h2>
            <p>생성 프로필을 저장하려면 먼저 3턴 인터뷰를 완료해야 합니다.</p>
            <div className="button-row">
              <Link className="ghost-button button-link" to={`/project/${projectId}`}>
                프로젝트로 돌아가기
              </Link>
              <Link className="primary-button button-link" to={`/project/${projectId}/interview`}>
                인터뷰로 이동
              </Link>
            </div>
          </div>
        ) : (
          <form className="stack-form" onSubmit={handleSave}>
            <label>
              업종
              <input
                value={profile.industry}
                onChange={(event) =>
                  setProfile({ ...profile, industry: event.target.value })
                }
                placeholder="예: 헤드스파, 카페, 레스토랑"
              />
            </label>

            <label>
              톤
              <select
                value={profile.tone}
                onChange={(event) =>
                  setProfile({ ...profile, tone: event.target.value })
                }
              >
                <option value="friendly">친근함</option>
                <option value="premium">프리미엄</option>
                <option value="warm">따뜻함</option>
                <option value="professional">전문적</option>
              </select>
            </label>

            <label>
              콘텐츠 길이
              <select
                value={profile.contentLength}
                onChange={(event) =>
                  setProfile({ ...profile, contentLength: event.target.value })
                }
              >
                <option value="short">짧게</option>
                <option value="standard">보통</option>
                <option value="long">길게</option>
              </select>
            </label>

            <label>
              강조 포인트
              <textarea
                rows={4}
                value={profile.emphasisPoint}
                onChange={(event) =>
                  setProfile({ ...profile, emphasisPoint: event.target.value })
                }
                placeholder="생성 결과에서 가장 강조해야 할 포인트를 입력하세요."
              />
            </label>

            <label>
              반드시 포함할 키워드
              <input
                value={listToText(profile.mustIncludeKeywords)}
                onChange={(event) =>
                  setProfile({
                    ...profile,
                    mustIncludeKeywords: event.target.value
                      .split(",")
                      .map((item) => item.trim())
                      .filter(Boolean),
                  })
                }
                placeholder="예: 성수 헤드스파, 프리미엄 두피 케어"
              />
            </label>

            <label>
              제외할 표현
              <input
                value={listToText(profile.excludedPhrases)}
                onChange={(event) =>
                  setProfile({
                    ...profile,
                    excludedPhrases: event.target.value
                      .split(",")
                      .map((item) => item.trim())
                      .filter(Boolean),
                  })
                }
                placeholder="예: 가성비 최고, 무조건 방문"
              />
            </label>

            <div className="panel nested-panel">
              <h2>사진 우선순위</h2>
              <p>자산을 누르면 생성 우선순위의 맨 앞으로 이동합니다.</p>
              <div className="media-list">
                {sortedMedia.map((asset) => (
                  <button
                    key={asset.id}
                    className={`media-card ${
                      profile.photoPriority[0] === asset.id ? "hero-media" : ""
                    }`}
                    type="button"
                    onClick={() => togglePriority(asset.id)}
                  >
                    <div className="media-card-top">
                      <strong>{asset.fileName}</strong>
                      <span>{profile.photoPriority.indexOf(asset.id) + 1}</span>
                    </div>
                    <p>{asset.id}</p>
                  </button>
                ))}
              </div>
            </div>

            <label>
              대표 미디어
              <select
                value={profile.representativeMediaAssetId ?? ""}
                onChange={(event) =>
                  setProfile({
                    ...profile,
                    representativeMediaAssetId: event.target.value || null,
                  })
                }
              >
                <option value="">대표 미디어 선택</option>
                {sortedMedia.map((asset) => (
                  <option key={asset.id} value={asset.id}>
                    {asset.fileName}
                  </option>
                ))}
              </select>
            </label>

            <div className="button-row">
              <Link className="ghost-button button-link" to={`/project/${projectId}`}>
                프로젝트로 돌아가기
              </Link>
              <button
                className="secondary-button"
                disabled={busy}
                type="button"
                onClick={handleGenerateAll}
              >
                {busy ? "생성 중..." : "전체 콘텐츠 생성"}
              </button>
              <button className="primary-button" disabled={busy} type="submit">
                {busy ? "저장 중..." : "생성 프로필 저장"}
              </button>
            </div>
          </form>
        )}

        {error ? <p className="error-banner">{error}</p> : null}
      </div>
    </section>
  );
}
