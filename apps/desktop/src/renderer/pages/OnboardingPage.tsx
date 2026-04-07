import { useEffect, useMemo, useRef, useState } from "react";

type Props = {
  bootstrap: BootstrapState;
  onCompleted: (nextState: BootstrapState) => void;
};

function joinProjectPath(dataDir: string) {
  return dataDir.endsWith("\\") || dataDir.endsWith("/")
    ? `${dataDir}projects`
    : `${dataDir}\\projects`;
}

export function OnboardingPage({ bootstrap, onCompleted }: Props) {
  const [step, setStep] = useState(0);
  const [projectRootPath, setProjectRootPath] = useState(
    bootstrap.settings.projectRootPath ?? ""
  );
  const [apiKeys, setApiKeys] = useState({
    gemini: "",
    anthropic: "",
    openai: "",
  });
  const [dependencyCheck, setDependencyCheck] = useState<DependencyCheckResult | null>(
    bootstrap.settings.dependencyCheck
  );
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const smokeTriggered = useRef(false);

  const steps = useMemo(
    () => [
      "환영",
      "API 키",
      "프로젝트 폴더",
      "의존성 점검",
      "완료",
    ],
    []
  );

  async function handleSelectProjectFolder() {
    const selected = await window.thohago.onboarding.selectProjectFolder();
    if (selected) {
      setProjectRootPath(selected);
    }
  }

  async function handleDependencyCheck() {
    setBusy(true);
    setError(null);
    try {
      const report = await window.thohago.onboarding.checkDependencies();
      setDependencyCheck(report);
      setStep(3);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : String(nextError));
    } finally {
      setBusy(false);
    }
  }

  async function handleComplete() {
    setBusy(true);
    setError(null);
    try {
      const nextState = await window.thohago.onboarding.complete({
        projectRootPath: projectRootPath || joinProjectPath(bootstrap.paths.dataDir),
        apiKeys,
        dependencyCheck,
      });
      onCompleted(nextState);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : String(nextError));
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (!bootstrap.smokeMode || smokeTriggered.current) {
      return;
    }

    smokeTriggered.current = true;
    setTimeout(async () => {
      setProjectRootPath(joinProjectPath(bootstrap.paths.dataDir));
      const report = await window.thohago.onboarding.checkDependencies();
      setDependencyCheck(report);
      setStep(4);
      const nextState = await window.thohago.onboarding.complete({
        projectRootPath: joinProjectPath(bootstrap.paths.dataDir),
        apiKeys: {
          gemini: "",
          anthropic: "",
          openai: "",
        },
        dependencyCheck: report,
      });
      onCompleted(nextState);
    }, 250);
  }, [bootstrap, onCompleted]);

  return (
    <section className="page page-onboarding">
      <div className="panel hero-panel">
        <p className="eyebrow">기초 설정</p>
        <h1>데스크톱 시작 설정</h1>
        <p className="lede">
          이 단계의 목표는 라이브 생성 기능이 아니라, 안정적인 로컬 실행 환경을
          준비하는 것입니다.
        </p>
        <ol className="stepper">
          {steps.map((label, index) => (
            <li
              key={label}
              className={index === step ? "active" : index < step ? "done" : ""}
            >
              <span>{index + 1}</span>
              <strong>{label}</strong>
            </li>
          ))}
        </ol>
      </div>

      <div className="panel flow-panel">
        <div className="wizard-step">
          {step === 0 ? (
            <>
              <h2>환영합니다</h2>
              <p>
                이 화면에서는 온보딩 잠금, 로컬 설정 저장, Python 사이드카 실행 상태를 확인합니다.
              </p>
              <button className="primary-button" onClick={() => setStep(1)}>
                다음
              </button>
            </>
          ) : null}

          {step === 1 ? (
            <>
              <h2>AI API 키</h2>
              <p>
                지금은 선택 입력입니다. 비워두면 이후 생성 단계는 사용할 수 없습니다.
              </p>
              <label>
                Gemini API 키
                <input
                  type="password"
                  value={apiKeys.gemini}
                  onChange={(event) =>
                    setApiKeys((current) => ({
                      ...current,
                      gemini: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                Anthropic API 키
                <input
                  type="password"
                  value={apiKeys.anthropic}
                  onChange={(event) =>
                    setApiKeys((current) => ({
                      ...current,
                      anthropic: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                OpenAI API 키
                <input
                  type="password"
                  value={apiKeys.openai}
                  onChange={(event) =>
                    setApiKeys((current) => ({
                      ...current,
                      openai: event.target.value,
                    }))
                  }
                />
              </label>
              <div className="button-row">
                <button className="ghost-button" onClick={() => setStep(0)}>
                  이전
                </button>
                <button className="primary-button" onClick={() => setStep(2)}>
                  다음
                </button>
              </div>
            </>
          ) : null}

          {step === 2 ? (
            <>
              <h2>프로젝트 폴더</h2>
              <p>
                가져온 미디어와 생성 결과물을 기본으로 저장할 폴더를 선택하세요.
              </p>
              <label>
                프로젝트 루트
                <input
                  type="text"
                  value={projectRootPath}
                  onChange={(event) => setProjectRootPath(event.target.value)}
                  placeholder={joinProjectPath(bootstrap.paths.dataDir)}
                />
              </label>
              <div className="button-row">
                <button className="ghost-button" onClick={() => setStep(1)}>
                  이전
                </button>
                <button className="secondary-button" onClick={handleSelectProjectFolder}>
                  찾아보기
                </button>
                <button className="primary-button" onClick={() => setStep(3)}>
                  다음
                </button>
              </div>
            </>
          ) : null}

          {step === 3 ? (
            <>
              <h2>의존성 점검</h2>
              <p>
                Python은 지금 바로 필요합니다. FFmpeg는 이후 영상 단계에서 사용되므로 미리 확인합니다.
              </p>
              <div className="dependency-actions">
                <button className="secondary-button" disabled={busy} onClick={handleDependencyCheck}>
                  {busy ? "확인 중..." : "의존성 점검 실행"}
                </button>
              </div>
              {dependencyCheck ? (
                <div className="dependency-grid">
                  <article className="dependency-card">
                    <h3>Python</h3>
                    <strong className={dependencyCheck.python.available ? "ok" : "bad"}>
                      {dependencyCheck.python.available ? "사용 가능" : "없음"}
                    </strong>
                    <code>{dependencyCheck.python.command}</code>
                    <p>{dependencyCheck.python.stdout || dependencyCheck.python.error || dependencyCheck.python.stderr}</p>
                  </article>
                  <article className="dependency-card">
                    <h3>FFmpeg</h3>
                    <strong className={dependencyCheck.ffmpeg.available ? "ok" : "bad"}>
                      {dependencyCheck.ffmpeg.available ? "사용 가능" : "없음"}
                    </strong>
                    <code>{dependencyCheck.ffmpeg.command}</code>
                    <p>{dependencyCheck.ffmpeg.stdout || dependencyCheck.ffmpeg.error || dependencyCheck.ffmpeg.stderr}</p>
                  </article>
                </div>
              ) : null}
              <div className="button-row">
                <button className="ghost-button" onClick={() => setStep(2)}>
                  이전
                </button>
                <button
                  className="primary-button"
                  onClick={() => setStep(4)}
                  disabled={!dependencyCheck}
                >
                  다음
                </button>
              </div>
            </>
          ) : null}

          {step === 4 ? (
            <>
              <h2>준비 완료</h2>
              <div className="summary-grid">
                <article>
                  <span>프로젝트 루트</span>
                  <strong>{projectRootPath || joinProjectPath(bootstrap.paths.dataDir)}</strong>
                </article>
                <article>
                  <span>Gemini 키</span>
                  <strong>{apiKeys.gemini ? "저장됨" : "지금은 건너뜀"}</strong>
                </article>
                <article>
                  <span>Python</span>
                  <strong>{dependencyCheck?.python.available ? "준비됨" : "확인 필요"}</strong>
                </article>
                <article>
                  <span>FFmpeg</span>
                  <strong>{dependencyCheck?.ffmpeg.available ? "준비됨" : "지금은 선택 사항"}</strong>
                </article>
              </div>
              <div className="button-row">
                <button className="ghost-button" onClick={() => setStep(3)}>
                  이전
                </button>
                <button className="primary-button" disabled={busy} onClick={handleComplete}>
                  {busy ? "저장 중..." : "기초 설정 완료"}
                </button>
              </div>
            </>
          ) : null}

          {error ? <p className="error-banner">{error}</p> : null}
        </div>
      </div>
    </section>
  );
}
