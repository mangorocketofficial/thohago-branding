interface DependencyCheckResult {
  checkedAt: string;
  python: {
    command: string;
    available: boolean;
    status: number | null;
    stdout: string;
    stderr: string;
    error: string | null;
  };
  ffmpeg: {
    command: string;
    available: boolean;
    status: number | null;
    stdout: string;
    stderr: string;
    error: string | null;
  };
  sidecar: {
    state: string;
    pid: number | null;
    lastError: string | null;
    restartAttempts: number;
    startedAt: string | null;
    connectedAt: string | null;
  };
}

interface MediaAsset {
  id: string;
  projectId: string;
  kind: "photo" | "video";
  sourceFilePath: string;
  filePath: string;
  fileName: string;
  mimeType: string | null;
  experienceOrder: number;
  isHero: boolean;
  createdAt: string;
}

interface MediaPreflight {
  ok: boolean;
  summary: string;
  photoCount?: number;
  videoCount?: number;
  photo_count?: number;
  video_count?: number;
  heroSuggestionId?: string | null;
  hero_suggestion_id?: string | null;
  experienceSequence?: Array<Record<string, unknown>>;
  experience_sequence?: Array<Record<string, unknown>>;
  notes?: string[];
}

interface GenerationProfile {
  industry: string;
  tone: string;
  contentLength: string;
  emphasisPoint: string;
  mustIncludeKeywords: string[];
  excludedPhrases: string[];
  photoPriority: string[];
  representativeMediaAssetId: string | null;
}

interface InterviewPlanner {
  ok: boolean;
  turnIndex?: number;
  turn_index?: number;
  strategy: string;
  coveredElements?: string[];
  covered_elements?: string[];
  missingElements?: string[];
  missing_elements?: string[];
  nextQuestion?: string;
  next_question?: string;
}

interface InterviewSession {
  id: string;
  projectId: string;
  status: string;
  preflight: MediaPreflight | null;
  turn1Question: string | null;
  turn1Answer: string | null;
  turn2Question: string | null;
  turn2Answer: string | null;
  turn3Question: string | null;
  turn3Answer: string | null;
  plannerTurn2: InterviewPlanner | null;
  plannerTurn3: InterviewPlanner | null;
  createdAt: string;
  updatedAt: string;
}

interface ProjectSummary {
  id: string;
  name: string;
  shopDisplayName: string;
  summary: string;
  projectFolderPath: string;
  mediaFolderPath: string;
  heroMediaAssetId: string | null;
  preflight: MediaPreflight | null;
  generationProfile: GenerationProfile | null;
  status: string;
  mediaCount: number;
  generatedContentCount: number;
  latestInterviewStatus: string | null;
  createdAt: string;
  updatedAt: string;
}

interface ProjectDetail extends ProjectSummary {
  mediaAssets: MediaAsset[];
  contentSpecs: ContentSpec[];
  publishRuns: PublishRun[];
  publishedContentCount: number;
  latestInterview: InterviewSession | null;
}

interface ContentSpec {
  id: string;
  projectId: string;
  contentType: "blog" | "carousel" | "video" | "thread";
  spec: Record<string, unknown>;
  artifactPath: string | null;
  previewArtifactPath: string | null;
  status: string;
  createdAt: string;
  updatedAt: string;
}

interface GenerationRun {
  id: string;
  mode: string;
  directive: Record<string, unknown>;
  spec: Record<string, unknown>;
  artifactPath: string | null;
  previewArtifactPath: string | null;
  createdAt: string;
}

interface PublishRun {
  id: string;
  contentType: "blog" | "carousel" | "video" | "thread";
  platform: string;
  executionMode: "mock" | "live";
  status: string;
  permalink: string | null;
  result: Record<string, unknown>;
  artifactPath: string | null;
  createdAt: string;
}

interface PublishSummaryItem {
  contentType: "blog" | "carousel" | "video" | "thread";
  platform: string;
  supportTier: "live_api" | "manual_handoff";
  liveStatus: "manual_ready" | "ready" | "blocked" | "attention" | "needs_validation";
  liveButtonLabel: string;
  recommendedAction: string;
  canRunLive: boolean;
  canRunLiveRecommended: boolean;
  latestRun: PublishRun | null;
  validationStatus: string | null;
  validationMessage: string;
}

interface PublishSummary {
  projectId: string;
  counts: {
    total: number;
    manualReady: number;
    liveReady: number;
    blocked: number;
    attention: number;
    published: number;
  };
  items: PublishSummaryItem[];
}

interface PublishCredentialStatus {
  instagram: {
    accessTokenPresent: boolean;
    instagramBusinessAccountId: string;
    facebookPageId: string;
    instagramGraphVersion: string;
  };
  threads: {
    accessTokenPresent: boolean;
    threadsUserId: string;
    facebookPageId: string;
  };
  naver: {
    liveNotePresent: boolean;
    naverLiveNote: string;
  };
  validation: {
    instagram: Record<string, unknown> | null;
    threads: Record<string, unknown> | null;
    naver: Record<string, unknown> | null;
  };
  lastValidation?: Record<string, unknown>;
}

interface BootstrapState {
  appTitle: string;
  version: string;
  smokeMode: boolean;
  smokeFlow: string;
  paths: {
    dataDir: string;
    dbPath: string;
    logsDir: string;
  };
  settings: {
    onboardingCompleted: boolean;
    projectRootPath: string | null;
    dependencyCheck: DependencyCheckResult | null;
    apiKeys: {
      gemini: boolean;
      anthropic: boolean;
      openai: boolean;
    };
    publishCredentials: PublishCredentialStatus;
  };
  sidecar: {
    state: string;
    pid: number | null;
    lastError: string | null;
    restartAttempts: number;
    startedAt: string | null;
    connectedAt: string | null;
  };
}

interface InspectableSetting {
  key: string;
  is_encrypted: number;
  updated_at: string;
}

interface Phase2SmokeScenarioResult {
  projectId: string;
  sessionId: string;
  projectFolderPath: string;
  mediaCount: number;
  interviewStatus: string;
}

interface Phase3SmokeScenarioResult extends Phase2SmokeScenarioResult {
  projectStatus: string;
  generationProfile: GenerationProfile | null;
}

interface Window {
  thohago: {
    app: {
      getBootstrap: () => Promise<BootstrapState>;
      reportSnapshot: (snapshot: Record<string, unknown>) => Promise<{ recorded: boolean }>;
      runPhase2SmokeScenario: () => Promise<Phase2SmokeScenarioResult>;
      runPhase3SmokeScenario: () => Promise<Phase3SmokeScenarioResult>;
    };
    onboarding: {
      checkDependencies: () => Promise<DependencyCheckResult>;
      complete: (payload: {
        projectRootPath: string;
        apiKeys: {
          gemini: string;
          anthropic: string;
          openai: string;
        };
        dependencyCheck: DependencyCheckResult | null;
      }) => Promise<BootstrapState>;
      selectProjectFolder: () => Promise<string | null>;
    };
    sidecar: {
      getStatus: () => Promise<BootstrapState["sidecar"]>;
      ping: () => Promise<{ ok: boolean; message: string; now: string }>;
      getSystemStatus: () => Promise<Record<string, unknown>>;
    };
    settings: {
      listInspectable: () => Promise<InspectableSetting[]>;
    };
    projects: {
      list: () => Promise<ProjectSummary[]>;
      create: (payload: {
        name: string;
        shopDisplayName: string;
        summary: string;
      }) => Promise<ProjectDetail>;
      get: (projectId: string) => Promise<ProjectDetail>;
      selectMediaFiles: () => Promise<string[]>;
      importMedia: (payload: {
        projectId: string;
        filePaths: string[];
      }) => Promise<ProjectDetail>;
      setHeroMedia: (payload: {
        projectId: string;
        mediaAssetId: string;
      }) => Promise<ProjectDetail>;
      updateMediaOrder: (payload: {
        projectId: string;
        orderedAssetIds: string[];
      }) => Promise<ProjectDetail>;
      buildPreflight: (projectId: string) => Promise<ProjectDetail>;
      getGenerationDefaults: (projectId: string) => Promise<GenerationProfile>;
      saveGenerationProfile: (payload: {
        projectId: string;
        profile: GenerationProfile;
      }) => Promise<ProjectDetail>;
    };
    content: {
      generateAll: (projectId: string) => Promise<ProjectDetail>;
      getSpec: (
        projectId: string,
        contentType: "blog" | "carousel" | "video" | "thread"
      ) => Promise<ContentSpec | null>;
      getPreviewHtml: (
        projectId: string,
        contentType: "blog" | "carousel" | "video" | "thread"
      ) => Promise<{ previewArtifactPath: string; html: string } | null>;
      regenerate: (payload: {
        projectId: string;
        contentType: "blog" | "carousel" | "video" | "thread";
        mode:
          | "regenerate"
          | "tone_shift"
          | "length_shorter"
          | "length_longer"
          | "premium"
          | "cta_boost";
      }) => Promise<ProjectDetail>;
      getRuns: (
        projectId: string,
        contentType: "blog" | "carousel" | "video" | "thread"
      ) => Promise<GenerationRun[]>;
    };
    interview: {
      get: (projectId: string) => Promise<InterviewSession | null>;
      start: (projectId: string) => Promise<InterviewSession>;
      submitAnswer: (payload: {
        projectId: string;
        answer: string;
      }) => Promise<InterviewSession>;
    };
    publish: {
      run: (payload: {
        projectId: string;
        contentType: "blog" | "carousel" | "video" | "thread";
        executionMode?: "mock" | "live";
      }) => Promise<ProjectDetail>;
      getRuns: (projectId: string) => Promise<PublishRun[]>;
      getSummary: (projectId: string) => Promise<PublishSummary>;
      runRecommended: (projectId: string) => Promise<{
        project: ProjectDetail;
        attemptedContentTypes: Array<"blog" | "carousel" | "video" | "thread">;
        summary: PublishSummary;
      }>;
      getCredentialStatus: () => Promise<PublishCredentialStatus>;
      saveCredentials: (payload: {
        graphMetaAccessToken: string;
        instagramBusinessAccountId: string;
        facebookPageId: string;
        instagramGraphVersion: string;
        threadsAccessToken: string;
        threadsUserId: string;
        naverLiveNote: string;
      }) => Promise<PublishCredentialStatus>;
      validateProvider: (
        provider: "instagram" | "threads" | "naver"
      ) => Promise<PublishCredentialStatus>;
    };
  };
}
