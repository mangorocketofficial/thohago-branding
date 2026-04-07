import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

function getCurrentQuestion(session: InterviewSession | null) {
  if (!session) {
    return null;
  }
  if (!session.turn1Answer) {
    return session.turn1Question;
  }
  if (!session.turn2Answer) {
    return session.turn2Question;
  }
  if (!session.turn3Answer) {
    return session.turn3Question;
  }
  return null;
}

export function InterviewPage() {
  const navigate = useNavigate();
  const params = useParams();
  const projectId = params.projectId as string;
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [session, setSession] = useState<InterviewSession | null>(null);
  const [answer, setAnswer] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadAll() {
    const [projectDetail, interviewSession] = await Promise.all([
      window.thohago.projects.get(projectId),
      window.thohago.interview.get(projectId),
    ]);
    setProject(projectDetail);
    setSession(interviewSession);
  }

  useEffect(() => {
    loadAll().catch((nextError) => {
      setError(nextError instanceof Error ? nextError.message : String(nextError));
    });
  }, [projectId]);

  useEffect(() => {
    if (!session) {
      return;
    }

    window.thohago.app.reportSnapshot({
      route: `/project/${projectId}/interview`,
      onboardingCompleted: true,
      projectId,
      interviewStatus: session.status,
      answeredTurns: [session.turn1Answer, session.turn2Answer, session.turn3Answer].filter(
        Boolean
      ).length,
    });
  }, [projectId, session]);

  const history = useMemo(() => {
    if (!session) {
      return [];
    }
    const rows = [];
    if (session.turn1Question) {
      rows.push({ role: "assistant", text: session.turn1Question });
    }
    if (session.turn1Answer) {
      rows.push({ role: "user", text: session.turn1Answer });
    }
    if (session.turn2Question) {
      rows.push({ role: "assistant", text: session.turn2Question });
    }
    if (session.turn2Answer) {
      rows.push({ role: "user", text: session.turn2Answer });
    }
    if (session.turn3Question) {
      rows.push({ role: "assistant", text: session.turn3Question });
    }
    if (session.turn3Answer) {
      rows.push({ role: "user", text: session.turn3Answer });
    }
    return rows;
  }, [session]);

  async function handleStart() {
    setBusy(true);
    setError(null);
    try {
      setSession(await window.thohago.interview.start(projectId));
      const nextProject = await window.thohago.projects.get(projectId);
      setProject(nextProject);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : String(nextError));
    } finally {
      setBusy(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const updated = await window.thohago.interview.submitAnswer({
        projectId,
        answer,
      });
      setSession(updated);
      setAnswer("");
      const nextProject = await window.thohago.projects.get(projectId);
      setProject(nextProject);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : String(nextError));
    } finally {
      setBusy(false);
    }
  }

  if (!project) {
    return (
      <div className="loading-shell">
        <h1>인터뷰를 불러오는 중입니다...</h1>
      </div>
    );
  }

  const currentQuestion = getCurrentQuestion(session);

  return (
    <section className="page page-interview">
      <div className="panel interview-header">
        <div>
          <p className="eyebrow">인터뷰</p>
          <h1>{project.shopDisplayName}</h1>
          <p className="lede">
            3번의 질문과 답변은 디스크에 저장되며, 사이드카가 preflight와 이전 답변을 기준으로 다음 질문을 계획합니다.
          </p>
        </div>
        <div className="button-row">
          <Link className="ghost-button button-link" to={`/project/${projectId}`}>
            프로젝트로 돌아가기
          </Link>
          {session?.status === "completed" ? (
            <button className="primary-button" onClick={() => navigate(`/project/${projectId}`)}>
              인터뷰 완료
            </button>
          ) : null}
        </div>
      </div>

      {error ? <p className="error-banner">{error}</p> : null}

      {!session ? (
        <div className="panel">
          <h2>인터뷰 시작</h2>
          <p>
            미디어가 있고 preflight가 준비되면 인터뷰를 시작할 수 있습니다. 현재 버전은 계약상 텍스트 입력 중심입니다.
          </p>
          <button className="primary-button" disabled={busy} onClick={handleStart}>
            {busy ? "시작 중..." : "3턴 인터뷰 시작"}
          </button>
        </div>
      ) : (
        <>
          <div className="panel">
            <h2>대화 기록</h2>
            <div className="chat-stack">
              {history.map((entry, index) => (
                <div
                  key={`${entry.role}-${index}`}
                  className={`chat-bubble chat-${entry.role}`}
                >
                  {entry.text}
                </div>
              ))}
            </div>
          </div>

          {session.status !== "completed" && currentQuestion ? (
            <form className="panel stack-form" onSubmit={handleSubmit}>
              <h2>현재 질문</h2>
              <p className="current-question">{currentQuestion}</p>
              <label>
                답변
                <textarea
                  required
                  value={answer}
                  onChange={(event) => setAnswer(event.target.value)}
                  placeholder="한국어나 영어로 입력할 수 있습니다. 입력한 텍스트는 그대로 저장됩니다."
                  rows={5}
                />
              </label>
              <div className="button-row">
                <button className="primary-button" disabled={busy} type="submit">
                  {busy ? "저장 중..." : "답변 제출"}
                </button>
              </div>
            </form>
          ) : null}

          {session.status === "completed" ? (
            <div className="panel">
              <h2>인터뷰 완료</h2>
              <p>
                세 번의 답변이 모두 저장되었습니다. 이제 생성 설정 단계로 이동할 수 있습니다.
              </p>
              <button className="primary-button" onClick={() => navigate(`/project/${projectId}`)}>
                프로젝트 화면으로 돌아가기
              </button>
            </div>
          ) : null}
        </>
      )}
    </section>
  );
}
