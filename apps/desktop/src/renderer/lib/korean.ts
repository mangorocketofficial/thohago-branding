export function translateSidecarState(state: string) {
  return {
    stopped: "중지됨",
    starting: "시작 중",
    connected: "연결됨",
    error: "오류",
  }[state] ?? state;
}

export function translateProjectStatus(status: string | null | undefined) {
  return {
    created: "생성됨",
    media_ready: "미디어 준비됨",
    interviewing: "인터뷰 진행 중",
    interview_completed: "인터뷰 완료",
    ready_to_generate: "생성 준비 완료",
    content_generated: "콘텐츠 생성 완료",
    published: "발행 완료",
    ready: "준비됨",
    draft: "초안",
    rendering: "렌더링 중",
  }[String(status || "")] ?? String(status || "-");
}

export function translateInterviewStatus(status: string | null | undefined) {
  return {
    pending: "대기 중",
    turn_1: "1차 질문",
    turn_2: "2차 질문",
    turn_3: "3차 질문",
    completed: "완료",
  }[String(status || "")] ?? (status ? String(status) : "시작 전");
}

export function translateContentType(contentType: string | null | undefined) {
  return {
    blog: "블로그",
    carousel: "캐러셀",
    video: "영상",
    thread: "스레드",
  }[String(contentType || "")] ?? String(contentType || "-");
}

export function translateContentTypeTitle(contentType: string | null | undefined) {
  return {
    blog: "블로그 검토",
    carousel: "캐러셀 검토",
    video: "영상 검토",
    thread: "스레드 검토",
  }[String(contentType || "")] ?? translateContentType(contentType);
}

export function translateGenerationMode(mode: string | null | undefined) {
  return {
    initial: "초기 생성",
    regenerate: "다시 생성",
    tone_shift: "톤 변경",
    length_shorter: "짧게",
    length_longer: "길게",
    premium: "더 프리미엄하게",
    cta_boost: "CTA 강화",
  }[String(mode || "")] ?? String(mode || "-");
}

export function translateTone(tone: string | null | undefined) {
  return {
    friendly: "친근함",
    premium: "프리미엄",
    warm: "따뜻함",
    professional: "전문적",
  }[String(tone || "")] ?? String(tone || "-");
}

export function translateContentLength(length: string | null | undefined) {
  return {
    short: "짧게",
    standard: "보통",
    long: "길게",
  }[String(length || "")] ?? String(length || "-");
}

export function translatePublishStatus(status: string | null | undefined) {
  return {
    ready: "준비됨",
    published: "발행 완료",
    missing: "자격 증명 부족",
    missing_media: "미디어 없음",
    error: "오류",
    unsupported: "직접 발행 미지원",
    manual_ready: "수동 패키지 준비됨",
    not_checked: "미확인",
    unknown: "알 수 없음",
  }[String(status || "")] ?? String(status || "-");
}

export function translateExecutionMode(mode: string | null | undefined) {
  return {
    mock: "모의 발행",
    live: "라이브 발행",
  }[String(mode || "")] ?? String(mode || "-");
}

export function translateSupportTier(tier: string | null | undefined) {
  return {
    live_api: "라이브 API",
    manual_handoff: "수동 패키지",
  }[String(tier || "")] ?? String(tier || "-");
}

export function translateLiveStatus(status: string | null | undefined) {
  return {
    manual_ready: "수동 패키지 준비됨",
    ready: "라이브 발행 가능",
    blocked: "차단됨",
    attention: "확인 필요",
    needs_validation: "검증 필요",
  }[String(status || "")] ?? String(status || "-");
}

export function translateProviderMessage(message: string | null | undefined) {
  const value = String(message || "").trim();
  if (!value) {
    return "표시할 메시지가 없습니다.";
  }

  const exactMap: Record<string, string> = {
    "No live validation has been recorded yet.": "아직 라이브 검증 기록이 없습니다.",
    "No provider message returned.": "프로바이더 메시지가 없습니다.",
    "Instagram live credentials are incomplete.": "인스타그램 라이브 발행 자격 증명이 완전하지 않습니다.",
    "Threads live credentials are incomplete.": "Threads 라이브 발행 자격 증명이 완전하지 않습니다.",
    "Naver live credential notes are saved, but live Naver publishing is not implemented in this phase.":
      "네이버 라이브 메모는 저장되었지만, 현재 단계에서는 네이버 직접 발행이 구현되어 있지 않습니다.",
    "Live Naver Blog publishing is not implemented in desktop phase 9.":
      "현재 데스크톱 트랙에서는 네이버 블로그 직접 발행이 구현되어 있지 않습니다.",
    "Live Instagram Reels publishing is not implemented in desktop phase 9.":
      "현재 데스크톱 트랙에서는 인스타그램 릴스 직접 발행이 구현되어 있지 않습니다.",
    "Naver Blog manual handoff package is ready.": "네이버 블로그 수동 업로드 패키지가 준비되었습니다.",
    "Instagram Reels manual handoff package is ready.": "인스타그램 릴스 수동 업로드 패키지가 준비되었습니다.",
    "Provider is ready for live publish.": "라이브 발행 준비가 완료되었습니다.",
    "Run provider validation before live publish.": "라이브 발행 전에 프로바이더 검증을 실행하세요.",
    "No provider detail": "프로바이더 상세 정보가 없습니다.",
    "No provider message yet.": "아직 프로바이더 메시지가 없습니다.",
    "No summary available.": "요약 정보가 없습니다.",
    "Create Naver handoff package": "네이버 수동 업로드 패키지 만들기",
    "Create Reels handoff package": "릴스 수동 업로드 패키지 만들기",
    "Create Manual Package": "수동 업로드 패키지 만들기",
    "Save credentials": "자격 증명 저장",
    "Complete credentials": "자격 증명 보완",
    "Review credentials and retry": "자격 증명을 확인하고 다시 시도",
    "Run live publish": "라이브 발행 실행",
    "Live Publish": "라이브 발행",
    "Review manually": "직접 확인",
  };
  if (exactMap[value]) {
    return exactMap[value];
  }

  if (value.includes("Session has expired")) {
    return "메타 액세스 토큰 세션이 만료되었습니다.";
  }
  if (value.startsWith("Graph API error")) {
    return "메타 Graph API 오류가 발생했습니다.";
  }
  if (value.startsWith("Threads API error")) {
    return "Threads API 오류가 발생했습니다.";
  }

  return value;
}
