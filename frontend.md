Here is Claude's plan:                                                                                                                                                             
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
 Next.js 프론트엔드 + 백엔드 확장 구현 계획                                                                                                                                         
                                                                                                                                                                                  
 Context

 현재 FastAPI 백엔드 파이프라인(트렌드→대본→미디어→영상)에 Next.js 프론트엔드를 추가한다.
 사용자가 6단계 위자드 UI를 통해 각 파이프라인 스텝의 중간 산출물을 확인하고 다음 단계를 진행할 수 있도록 한다.
 또한 출연자를 가족 구성원 7명(나, 할머니, 할아버지, 지호, 지형, 지원, 아내) 중 선택 가능하게 하고,
 이미지 생성 시 assets/pic/ 사진을 참조하도록 한다.

 ---
 새로운 파이프라인 플로우

 trend_researcher → topic_selection_gate (NEW #1: 트렌드 결과 선택)
   → speaker_selection_gate (NEW #2: 출연자 선택)
   → scriptwriter → human_review_gate (#3: 대본 확인)
   → audio_choice_gate (#4: TTS/녹음 선택)
   → media_producer → auto_editor → END (영상 확인)

 6단계 위자드 UX

 ┌──────┬───────────────┬───────────────────────────────┬──────────────────────────────────────┐
 │ Step │     이름      │            트리거             │             사용자 액션              │
 ├──────┼───────────────┼───────────────────────────────┼──────────────────────────────────────┤
 │ 1    │ 카테고리 선택 │ 페이지 진입                   │ 카테고리 다중 선택 → 파이프라인 시작 │
 ├──────┼───────────────┼───────────────────────────────┼──────────────────────────────────────┤
 │ 2    │ 트렌드 결과   │ waiting_for_topic_selection   │ 토픽 1개 선택                        │
 ├──────┼───────────────┼───────────────────────────────┼──────────────────────────────────────┤
 │ 3    │ 출연자 선택   │ waiting_for_speaker_selection │ 사회자 1명 + 참여자 N명 선택         │
 ├──────┼───────────────┼───────────────────────────────┼──────────────────────────────────────┤
 │ 4    │ 대본 검토     │ waiting_for_review            │ 승인 또는 수정 요청                  │
 ├──────┼───────────────┼───────────────────────────────┼──────────────────────────────────────┤
 │ 5    │ 오디오 선택   │ waiting_for_audio_choice      │ TTS 또는 수동 녹음 선택              │
 ├──────┼───────────────┼───────────────────────────────┼──────────────────────────────────────┤
 │ 6    │ 영상 완성     │ completed                     │ 영상 재생 + 다운로드                 │
 └──────┴───────────────┴───────────────────────────────┴──────────────────────────────────────┘

 ---
 Part A: 백엔드 변경 (8개 파일)

 A1. graph/state.py — 새 state 필드 추가

 # PipelineState에 추가:
 topic_selected: Optional[str]
 topic_selection_approved: Optional[bool]
 selected_speakers: Optional[dict]  # {"host": "me", "participants": ["grandma", "jiho"]}
 speaker_selection_approved: Optional[bool]

 A2. nodes/topic_selection.py — 신규 파일

 - topic_selection_gate(state) → interrupt() 로 트렌드 결과 제시
 - interrupt data: {"type": "topic_selection", "topics": topic_summaries}
 - resume payload: {"selected_topic": "키워드"}
 - 선택된 토픽으로 trend_data.selected_topic 업데이트

 A3. nodes/speaker_selection.py — 신규 파일

 - speaker_selection_gate(state) → interrupt() 로 가족 멤버 제시
 - FAMILY_MEMBERS dict 정의:
 {
   "me": {"name": "나"}, "grandma": {"name": "할머니"}, "grandfa": {"name": "할아버지"},
   "jiho": {"name": "지호"}, "jihyung": {"name": "지형"}, "jiwon": {"name": "지원"}, "wife": {"name": "아내"}
 }
 - resume payload: {"host": "me", "participants": ["jiho", "jiwon"]}

 A4. graph/edges.py

 - route_after_trend() 반환값: "scriptwriter" → "topic_selection_gate"

 A5. graph/builder.py

 - topic_selection_gate, speaker_selection_gate 노드 등록
 - 라우팅: trend_researcher → topic_selection_gate → speaker_selection_gate → scriptwriter

 A6. nodes/scriptwriter.py — 동적 화자 지원

 - state.get("selected_speakers") 에서 host/participants 읽기
 - FAMILY_MEMBERS 로 화자 이름/역할 동적 생성
 - SCRIPT_SYSTEM_PROMPT 를 동적 화자 정보로 포맷팅
 - speaker_label 매핑도 동적 구성 (예: {"host": "할아버지", "participant_1": "지호"})

 A7. api/routes.py + api/schemas.py

 신규 엔드포인트:
 - GET /{run_id}/topics — 트렌드 결과 조회
 - POST /{run_id}/topic-selection — 토픽 선택 제출
 - GET /{run_id}/speakers — 출연자 목록 조회
 - POST /{run_id}/speaker-selection — 출연자 선택 제출

 신규 스키마:
 - TopicSelectionRequest(selected_topic: str)
 - SpeakerSelectionRequest(host: str, participants: list[str])

 상태 감지 추가:
 - "waiting_for_topic_selection" (topic_selection_gate 인터럽트)
 - "waiting_for_speaker_selection" (speaker_selection_gate 인터럽트)

 A8. main.py — CORS + 정적 파일 서빙

 # CORS
 app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], ...)

 # Static files
 app.mount("/files/output", StaticFiles(directory="output"), name="output")
 app.mount("/files/assets", StaticFiles(directory="assets"), name="assets")

 ---
 Part B: 프론트엔드 구현

 B1. 프로젝트 구조

 위치: /Applications/workspace/Podcast/podcast-shorts-frontend/

 src/
   app/
     layout.tsx              # 루트 레이아웃 (한국어, 다크 테마)
     page.tsx                # 위자드 메인 페이지
     globals.css
   components/
     wizard/
       WizardLayout.tsx      # 스텝 인디케이터 + 콘텐츠
       StepIndicator.tsx     # 상단 진행 바
       Step1Category.tsx     # 카테고리 선택 그리드
       Step2TrendResults.tsx # 트렌드 토픽 카드 리스트
       Step3Speakers.tsx     # 가족 사진 그리드 (사회자/참여자)
       Step4ScriptReview.tsx # 대본 장면 카드 + 승인/거절
       Step5AudioChoice.tsx  # TTS vs 수동 녹음 선택
       Step6VideoResult.tsx  # 영상 플레이어 + 메타데이터
     ui/
       Button.tsx, Card.tsx, Badge.tsx, Spinner.tsx
   lib/
     api.ts                  # fetch 기반 API 클라이언트
     types.ts                # TypeScript 인터페이스
     constants.ts            # 카테고리, 가족 멤버, API_BASE
     hooks/
       usePipeline.ts        # 파이프라인 오케스트레이션 훅
       usePolling.ts         # 상태 폴링 훅
   context/
     PipelineContext.tsx      # useReducer 기반 전역 상태

 B2. 기술 스택

 - Next.js 14+ (App Router, TypeScript)
 - Tailwind CSS (다크 테마)
 - lucide-react (아이콘)
 - React Context + useReducer (상태 관리)

 B3. 핵심 상수 (lib/constants.ts)

 카테고리 10개:
 기술, 엔터테인먼트, 사회, 경제, 스포츠, 정치, 문화, 과학, 건강, 교육

 가족 멤버 7명:
 me(나), grandma(할머니), grandfa(할아버지), jiho(지호), jihyung(지형), jiwon(지원), wife(아내)

 사진 URL: http://localhost:8000/files/assets/pic/{key}.jpeg

 B4. 폴링 전략 (usePolling 훅)

 - 2초 간격 폴링 (GET /status)
 - 인터럽트 상태 감지 시 → 해당 스텝으로 전환 + 폴링 중단
 - 사용자 액션 제출 후 → 폴링 재개
 - 상태→스텝 매핑:
   - running (trend_researcher) → Step 1 로딩
   - waiting_for_topic_selection → Step 2
   - waiting_for_speaker_selection → Step 3
   - running (scriptwriter) → Step 3 로딩
   - waiting_for_review → Step 4
   - waiting_for_audio_choice → Step 5
   - running (media_producer/auto_editor) → Step 5 로딩
   - completed → Step 6
   - failed → 에러 표시

 B5. 각 스텝 상세

 Step 1 (카테고리): 10개 카테고리 카드 그리드, 다중 선택, "시작" 버튼 → POST /start

 Step 2 (트렌드): 토픽 카드 리스트 (keyword, summary, source 배지, trending_score 바), 단일 선택 → POST /topic-selection

 Step 3 (출연자): 가족 사진 원형 그리드, 사회자(단일선택) + 참여자(다중선택) 분리, 최소 참여자 1명 필수 → POST /speaker-selection

 Step 4 (대본): 장면 카드 리스트 (화자 컬러 배지, 대사, 감정 태그), Hook/Body/CTA 그룹핑, 승인 or 수정요청(피드백 텍스트) → POST /review

 Step 5 (오디오): TTS/수동 대형 카드 2개, 수동 선택 시 assets/audio/ 파일 매핑 UI → POST /audio-choice

 Step 6 (영상): <video> 플레이어, 썸네일, 메타데이터 표시, 다운로드 버튼, "새로 시작" 버튼

 B6. 파일 경로 변환

 백엔드 로컬 경로 → 프론트엔드 URL 변환 유틸:
 function toFileUrl(path: string): string {
   // "output/{run_id}/..." → "http://localhost:8000/files/output/{run_id}/..."
 }

 ---
 Part C: 구현 순서

 Phase 1: 백엔드 API 확장

 1. graph/state.py — 새 필드 추가
 2. nodes/topic_selection.py — 신규 인터럽트 노드
 3. nodes/speaker_selection.py — 신규 인터럽트 노드
 4. graph/edges.py — route_after_trend 수정
 5. graph/builder.py — 새 노드 등록 + 라우팅
 6. api/schemas.py — 새 스키마
 7. api/routes.py — 새 엔드포인트 + 상태 감지
 8. main.py — CORS + 정적 파일 서빙
 9. _run_pipeline 초기 상태에 새 필드 추가

 Phase 2: 스크립트라이터 동적 화자

 10. nodes/scriptwriter.py — 동적 화자 프롬프트
 11. nodes/media_producer.py — 동적 voice_ids

 Phase 3: 프론트엔드 셋업

 12. Next.js 프로젝트 생성 (TypeScript + Tailwind)
 13. lib/types.ts, lib/constants.ts, lib/api.ts
 14. context/PipelineContext.tsx
 15. lib/hooks/usePolling.ts, lib/hooks/usePipeline.ts

 Phase 4: 프론트엔드 컴포넌트

 16. UI 프리미티브 (Button, Card, Badge, Spinner)
 17. WizardLayout + StepIndicator
 18. Step1~Step6 컴포넌트 순차 구현

 Phase 5: 통합 테스트

 19. E2E: 6단계 전체 플로우 실행
 20. 에러 상태 / 대본 수정 루프 테스트

 ---
 수정/생성 파일 목록

 백엔드 (10개)

 ┌────────────────────────────┬─────────────────────────────┐
 │            파일            │          변경 유형          │
 ├────────────────────────────┼─────────────────────────────┤
 │ graph/state.py             │ 새 state 필드 추가          │
 ├────────────────────────────┼─────────────────────────────┤
 │ nodes/topic_selection.py   │ 신규 — 토픽 선택 인터럽트   │
 ├────────────────────────────┼─────────────────────────────┤
 │ nodes/speaker_selection.py │ 신규 — 출연자 선택 인터럽트 │
 ├────────────────────────────┼─────────────────────────────┤
 │ graph/edges.py             │ route_after_trend 수정      │
 ├────────────────────────────┼─────────────────────────────┤
 │ graph/builder.py           │ 새 노드 + 라우팅            │
 ├────────────────────────────┼─────────────────────────────┤
 │ nodes/scriptwriter.py      │ 동적 화자 프롬프트          │
 ├────────────────────────────┼─────────────────────────────┤
 │ nodes/media_producer.py    │ 동적 voice_ids              │
 ├────────────────────────────┼─────────────────────────────┤
 │ api/schemas.py             │ 새 스키마 추가              │
 ├────────────────────────────┼─────────────────────────────┤
 │ api/routes.py              │ 새 엔드포인트 + 상태 감지   │
 ├────────────────────────────┼─────────────────────────────┤
 │ main.py                    │ CORS + 정적 파일 서빙       │
 └────────────────────────────┴─────────────────────────────┘

 프론트엔드 (신규 프로젝트, ~20개 파일)

 ┌─────────────────────────────┬───────────────────────┐
 │            파일             │         설명          │
 ├─────────────────────────────┼───────────────────────┤
 │ app/layout.tsx              │ 루트 레이아웃         │
 ├─────────────────────────────┼───────────────────────┤
 │ app/page.tsx                │ 메인 페이지           │
 ├─────────────────────────────┼───────────────────────┤
 │ lib/types.ts                │ TypeScript 타입       │
 ├─────────────────────────────┼───────────────────────┤
 │ lib/constants.ts            │ 상수 정의             │
 ├─────────────────────────────┼───────────────────────┤
 │ lib/api.ts                  │ API 클라이언트        │
 ├─────────────────────────────┼───────────────────────┤
 │ lib/hooks/usePolling.ts     │ 폴링 훅               │
 ├─────────────────────────────┼───────────────────────┤
 │ lib/hooks/usePipeline.ts    │ 오케스트레이션 훅     │
 ├─────────────────────────────┼───────────────────────┤
 │ context/PipelineContext.tsx │ 전역 상태             │
 ├─────────────────────────────┼───────────────────────┤
 │ components/ui/*.tsx         │ UI 프리미티브 (4개)   │
 ├─────────────────────────────┼───────────────────────┤
 │ components/wizard/*.tsx     │ 위자드 컴포넌트 (8개) │
 └─────────────────────────────┴───────────────────────┘

 ---
 검증 방법

 1. 백엔드: build_graph() 성공 + ruff lint 통과
 2. 백엔드: curl로 새 엔드포인트 테스트
 3. 프론트엔드: npm run dev → http://localhost:3000
 4. E2E: Step 1~6 전체 플로우 실행
 5. 출력 확인: ./output/{run_id}/ 파일 생성
 6. 영상 재생: 브라우저에서 최종 영상 재생 확인