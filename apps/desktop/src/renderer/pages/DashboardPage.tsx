import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { SidecarStatusBadge } from "../components/SidecarStatusBadge";
import { translateInterviewStatus, translateProjectStatus } from "../lib/korean";

type Props = {
  bootstrap: BootstrapState;
  onRefresh: () => Promise<void>;
};

export function DashboardPage({ bootstrap, onRefresh }: Props) {
  const navigate = useNavigate();
  const [inspectableSettings, setInspectableSettings] = useState<InspectableSetting[]>([]);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [pingResult, setPingResult] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const smokeTriggered = useRef(false);

  async function loadDashboardData() {
    const [settings, projectRows] = await Promise.all([
      window.thohago.settings.listInspectable(),
      window.thohago.projects.list(),
    ]);
    setInspectableSettings(settings);
    setProjects(projectRows);
  }

  useEffect(() => {
    loadDashboardData().catch((nextError) => {
      setError(nextError instanceof Error ? nextError.message : String(nextError));
    });
  }, [bootstrap.settings.onboardingCompleted]);

  useEffect(() => {
    if (!bootstrap.smokeMode || smokeTriggered.current) {
      return;
    }

    if (bootstrap.smokeFlow === "phase2") {
      smokeTriggered.current = true;
      setBusy(true);
      window.thohago.app
        .runPhase2SmokeScenario()
        .then(async (scenario) => {
          await loadDashboardData();
          navigate(`/project/${scenario.projectId}/interview`, { replace: true });
          setTimeout(() => {
            navigate(`/project/${scenario.projectId}`, { replace: true });
          }, 350);
        })
        .catch((nextError) => {
          setError(nextError instanceof Error ? nextError.message : String(nextError));
        })
        .finally(() => {
          setBusy(false);
        });
      return;
    }

    if (bootstrap.smokeFlow === "phase3") {
      smokeTriggered.current = true;
      setBusy(true);
      window.thohago.app
        .runPhase3SmokeScenario()
        .then(async (scenario) => {
          await loadDashboardData();
          navigate(`/project/${scenario.projectId}/generate`, { replace: true });
          setTimeout(() => {
            navigate(`/project/${scenario.projectId}`, { replace: true });
          }, 350);
        })
        .catch((nextError) => {
          setError(nextError instanceof Error ? nextError.message : String(nextError));
        })
        .finally(() => {
          setBusy(false);
        });
      return;
    }

    if (bootstrap.smokeFlow === "phase2-restart" && projects.length > 0) {
      smokeTriggered.current = true;
      navigate(`/project/${projects[0].id}`, { replace: true });
      return;
    }

    if (bootstrap.smokeFlow === "phase3-restart" && projects.length > 0) {
      smokeTriggered.current = true;
      navigate(`/project/${projects[0].id}/generate`, { replace: true });
      return;
    }

  }, [bootstrap.smokeFlow, bootstrap.smokeMode, navigate, projects]);

  async function handlePing() {
    const result = await window.thohago.sidecar.ping();
    setPingResult(`사이드카 응답: ${result.message} (${result.now})`);
    await onRefresh();
    await loadDashboardData();
  }

  return (
    <section className="page page-dashboard">
      <div className="panel dashboard-hero">
        <p className="eyebrow">프로젝트 허브</p>
        <h1>프로젝트와 인터뷰 준비 상태</h1>
        <p className="lede">
          매장 프로젝트를 만들고, 미디어를 가져오고, 이후 생성 단계의 기반이 되는
          3턴 인터뷰를 완료하세요.
        </p>
        <div className="hero-actions">
          <Link className="primary-button button-link" to="/project/new">
            새 프로젝트
          </Link>
          <button className="secondary-button" onClick={handlePing}>
            사이드카 확인
          </button>
          <button className="ghost-button" onClick={loadDashboardData}>
            프로젝트 새로고침
          </button>
        </div>
        {busy ? <p className="info-banner">자동 검증 시나리오를 실행 중입니다...</p> : null}
        {pingResult ? <p className="info-banner">{pingResult}</p> : null}
        {error ? <p className="error-banner">{error}</p> : null}
      </div>

      <div className="dashboard-grid">
        <article className="panel">
          <h2>프로젝트 목록</h2>
          <div className="project-list">
            {projects.length === 0 ? (
              <div className="empty-state">
                <strong>아직 프로젝트가 없습니다.</strong>
                <p>첫 프로젝트를 만들어 미디어 수집과 인터뷰 흐름을 시작하세요.</p>
              </div>
            ) : null}
            {projects.map((project) => (
              <Link
                key={project.id}
                className="project-card"
                to={`/project/${project.id}`}
              >
                <div className="project-card-top">
                  <strong>{project.shopDisplayName}</strong>
                  <span className={`status-pill status-${project.status}`}>
                    {translateProjectStatus(project.status)}
                  </span>
                </div>
                <p>{project.summary || "아직 요약이 없습니다."}</p>
                <dl className="inline-stats">
                  <div>
                    <dt>미디어</dt>
                    <dd>{project.mediaCount}</dd>
                  </div>
                  <div>
                    <dt>인터뷰</dt>
                    <dd>{translateInterviewStatus(project.latestInterviewStatus)}</dd>
                  </div>
                </dl>
              </Link>
            ))}
          </div>
        </article>

        <article className="panel">
          <h2>런타임</h2>
          <SidecarStatusBadge status={bootstrap.sidecar} />
          <dl className="detail-list compact">
            <div>
              <dt>프로젝트 루트</dt>
              <dd>{bootstrap.settings.projectRootPath ?? "설정되지 않음"}</dd>
            </div>
            <div>
              <dt>데이터 폴더</dt>
              <dd>{bootstrap.paths.dataDir}</dd>
            </div>
            <div>
              <dt>데이터베이스</dt>
              <dd>{bootstrap.paths.dbPath}</dd>
            </div>
          </dl>
        </article>

        <article className="panel">
          <h2>설정 상태</h2>
          <ul className="settings-list">
            {inspectableSettings.map((setting) => (
              <li key={setting.key}>
                <strong>{setting.key}</strong>
                <span>{setting.is_encrypted ? "암호화" : "일반"}</span>
                <code>{setting.updated_at}</code>
              </li>
            ))}
          </ul>
        </article>
      </div>
    </section>
  );
}
