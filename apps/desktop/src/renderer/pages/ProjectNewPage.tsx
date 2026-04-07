import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

export function ProjectNewPage() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [shopDisplayName, setShopDisplayName] = useState("");
  const [summary, setSummary] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const project = await window.thohago.projects.create({
        name,
        shopDisplayName,
        summary,
      });
      navigate(`/project/${project.id}`, { replace: true });
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : String(nextError));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="page page-form">
      <div className="panel form-panel">
        <p className="eyebrow">프로젝트 설정</p>
        <h1>새 데스크톱 프로젝트 만들기</h1>
        <p className="lede">
          프로젝트는 가져온 미디어, preflight, 인터뷰, 생성 결과물을 담는 로컬 작업 단위입니다.
        </p>
        <form className="stack-form" onSubmit={handleSubmit}>
          <label>
            내부 프로젝트 이름
            <input
              required
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="phase2-headspa"
            />
          </label>
          <label>
            매장 표시 이름
            <input
              required
              value={shopDisplayName}
              onChange={(event) => setShopDisplayName(event.target.value)}
              placeholder="예: 성수 헤드스파 라움"
            />
          </label>
          <label>
            짧은 요약
            <input
              value={summary}
              onChange={(event) => setSummary(event.target.value)}
              placeholder="예: 조용한 분위기, 프리미엄 두피 케어, 첫 방문 고객 환영"
            />
          </label>

          <div className="button-row">
            <Link className="ghost-button button-link" to="/">
              이전
            </Link>
            <button className="primary-button" disabled={busy} type="submit">
              {busy ? "생성 중..." : "프로젝트 만들기"}
            </button>
          </div>
        </form>
        {error ? <p className="error-banner">{error}</p> : null}
      </div>
    </section>
  );
}
