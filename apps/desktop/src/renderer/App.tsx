import { useEffect, useState } from "react";
import {
  HashRouter,
  Navigate,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";
import { DashboardPage } from "./pages/DashboardPage";
import { ContentReviewPage } from "./pages/ContentReviewPage";
import { GenerationSetupPage } from "./pages/GenerationSetupPage";
import { InterviewPage } from "./pages/InterviewPage";
import { OnboardingPage } from "./pages/OnboardingPage";
import { PublishPage } from "./pages/PublishPage";
import { ProjectNewPage } from "./pages/ProjectNewPage";
import { ProjectViewPage } from "./pages/ProjectViewPage";
import { SidecarStatusBadge } from "./components/SidecarStatusBadge";

function RouteReporter({ bootstrap }: { bootstrap: BootstrapState }) {
  const location = useLocation();

  useEffect(() => {
    window.thohago.app.reportSnapshot({
      route: location.pathname,
      onboardingCompleted: bootstrap.settings.onboardingCompleted,
      sidecarState: bootstrap.sidecar.state,
      projectRootPath: bootstrap.settings.projectRootPath,
    });
  }, [
    bootstrap.settings.onboardingCompleted,
    bootstrap.settings.projectRootPath,
    bootstrap.sidecar.state,
    location.pathname,
  ]);

  return null;
}

function RouterApp({
  bootstrap,
  setBootstrap,
}: {
  bootstrap: BootstrapState;
  setBootstrap: (state: BootstrapState) => void;
}) {
  async function refreshBootstrap() {
    setBootstrap(await window.thohago.app.getBootstrap());
  }

  return (
    <HashRouter>
      <RouteReporter bootstrap={bootstrap} />
      <div className="app-frame">
        <aside className="app-sidebar">
          <div>
            <p className="eyebrow">데스크톱 워크플로</p>
            <h2>{bootstrap.appTitle}</h2>
            <p className="sidebar-copy">
              프로젝트 생성, 인터뷰, 콘텐츠 생성, 재생성, 발행 흐름을
              데스크톱에서 순차적으로 진행할 수 있습니다.
            </p>
          </div>
          <div className="sidebar-status">
            <SidecarStatusBadge status={bootstrap.sidecar} />
          </div>
        </aside>

        <main className="app-main">
          <Routes>
            <Route
              path="/onboarding"
              element={
                bootstrap.settings.onboardingCompleted ? (
                  <Navigate to="/" replace />
                ) : (
                  <OnboardingPage bootstrap={bootstrap} onCompleted={setBootstrap} />
                )
              }
            />
            <Route
              path="/"
              element={
                bootstrap.settings.onboardingCompleted ? (
                  <DashboardPage bootstrap={bootstrap} onRefresh={refreshBootstrap} />
                ) : (
                  <Navigate to="/onboarding" replace />
                )
              }
            />
            <Route
              path="/project/new"
              element={
                bootstrap.settings.onboardingCompleted ? (
                  <ProjectNewPage />
                ) : (
                  <Navigate to="/onboarding" replace />
                )
              }
            />
            <Route
              path="/project/:projectId"
              element={
                bootstrap.settings.onboardingCompleted ? (
                  <ProjectViewPage />
                ) : (
                  <Navigate to="/onboarding" replace />
                )
              }
            />
            <Route
              path="/project/:projectId/interview"
              element={
                bootstrap.settings.onboardingCompleted ? (
                  <InterviewPage />
                ) : (
                  <Navigate to="/onboarding" replace />
                )
              }
            />
            <Route
              path="/project/:projectId/generate"
              element={
                bootstrap.settings.onboardingCompleted ? (
                  <GenerationSetupPage />
                ) : (
                  <Navigate to="/onboarding" replace />
                )
              }
            />
            <Route
              path="/project/:projectId/blog"
              element={bootstrap.settings.onboardingCompleted ? <ContentReviewPage contentType="blog" /> : <Navigate to="/onboarding" replace />}
            />
            <Route
              path="/project/:projectId/carousel"
              element={bootstrap.settings.onboardingCompleted ? <ContentReviewPage contentType="carousel" /> : <Navigate to="/onboarding" replace />}
            />
            <Route
              path="/project/:projectId/video"
              element={bootstrap.settings.onboardingCompleted ? <ContentReviewPage contentType="video" /> : <Navigate to="/onboarding" replace />}
            />
            <Route
              path="/project/:projectId/thread"
              element={bootstrap.settings.onboardingCompleted ? <ContentReviewPage contentType="thread" /> : <Navigate to="/onboarding" replace />}
            />
            <Route
              path="/project/:projectId/publish"
              element={bootstrap.settings.onboardingCompleted ? <PublishPage /> : <Navigate to="/onboarding" replace />}
            />
            <Route
              path="*"
              element={
                <Navigate
                  to={bootstrap.settings.onboardingCompleted ? "/" : "/onboarding"}
                  replace
                />
              }
            />
          </Routes>
        </main>
      </div>
    </HashRouter>
  );
}

export function App() {
  const [bootstrap, setBootstrap] = useState<BootstrapState | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    window.thohago.app
      .getBootstrap()
      .then(setBootstrap)
      .catch((nextError) => {
        setError(nextError instanceof Error ? nextError.message : String(nextError));
      });
  }, []);

  if (error) {
    return (
      <div className="loading-shell">
        <h1>데스크톱 초기화에 실패했습니다</h1>
        <p>{error}</p>
      </div>
    );
  }

  if (!bootstrap) {
    return (
      <div className="loading-shell">
        <h1>데스크톱 런타임을 준비하는 중입니다...</h1>
        <p>로컬 상태, 데이터베이스 마이그레이션, 사이드카 상태를 불러오고 있습니다.</p>
      </div>
    );
  }

  return <RouterApp bootstrap={bootstrap} setBootstrap={setBootstrap} />;
}
