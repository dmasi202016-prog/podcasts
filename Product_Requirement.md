AI 쇼츠 제작 플랫폼 아키텍처 요구사항 (LangChain 기반)

1. 프로젝트 개요
목적: 최신 트렌드를 분석하여 사용자의 목소리(또는 클론)를 입힌 3분 이내의 팟캐스트형 쇼츠 자동 생성.

핵심 가치: 트렌드 감지부터 배포까지의 Full-Automation 및 Personalized Voice.

개발 방식: LangChain/LangGraph를 활용한 멀티 에이전트 워크플로우.

2. 기능적 요구사항 (Functional Requirements)
Phase 1: 트렌드 리서처 에이전트 (Trend Researcher)

데이터 소스: Google Trends, YouTube 인기 급상승, X(Twitter) 실시간 트렌드 API 연동.

기능: * 현재 화제가 되는 키워드 추출 및 요약.

단순 검색을 넘어 '왜' 화제인지 분석하여 인사이트 제공.

사용자가 설정한 특정 관심 분야(IT, 경제, 연예 등) 필터링.

Phase 2: 팟캐스트 시나리오 작가 (Scriptwriter)

기능: * 리서치 데이터를 바탕으로 1~3분 분량의 대화형 대본 작성.

Podcast Style: 오프닝(후킹) - 본론(3단 구성) - 클로징(CTA) 구조.

Persona: 사용자 고유의 말투, 추임새(아 맞다, 그건 그렇고 등) 반영.

장면별 비주얼 생성을 위한 이미지 생성 프롬프트 자동 추출.

Phase 3: 보이스 및 미디어 생성 (Voice & Media Producer)

음성 구현: * ElevenLabs API 연동 (사용자 목소리 클로닝 모드 지원).

대본의 감정선에 따른 음성 톤 조절.

시각 자료: * DALL-E 3 또는 Midjourney를 이용한 문맥 맞춤형 이미지 생성.

필요 시 Luma/Runway API를 통한 5초 내외의 배경 비디오 생성.

Phase 4: 자동 편집 엔진 (Auto-Editor)

기능: * Python MoviePy 라이브러리를 사용한 오디오-비디오 합성.

OpenAI Whisper API를 통한 음성 기반 자동 자막(Caption) 생성.

BGM 자동 믹싱 및 사운드 효과 삽입.

3. 기술적 요구사항 (Technical Requirements)
🧩 LangChain 아키텍처 구성

LangGraph 활용: 각 단계(리서치 -> 대본 -> 생성 -> 편집)를 노드(Node)로 설정하고, 결과물이 미흡할 경우 이전 단계로 되돌리는 루프 구조 설계.

Memory 관리: ReadOnlySharedMemory를 통해 프로젝트 전체의 맥락(사용자 선호도, 이전 영상 스타일) 공유.

Tool Calling: 외부 검색 API(Tavily), 이미지 생성 API를 에이전트가 상황에 맞게 호출하도록 설계.

🛠 기술 스택

Orchestration: LangChain, LangGraph

LLM: GPT-4o (Main Reasoning), Claude 3.5 Sonnet (Creative Writing)

Audio: ElevenLabs API, Whisper API

Video/Image: Luma Dream Machine API, DALL-E 3

Backend: Python (FastAPI)

Video Processing: MoviePy, FFmpeg

4. 데이터 흐름 (Data Flow)
Input: 사용자 관심 키워드 혹은 자동 트렌드 탐색 시작.

Process 1 (LLM): 트렌드 분석 → 대본 생성 → 이미지 프롬프트 생성.

Process 2 (External API): 목소리 생성(.mp3) → 이미지 생성(.png) → 영상 소스 생성(.mp4).

Process 3 (Code Executor): 모든 소스를 MoviePy 노드에 투입하여 최종 렌더링.

Output: 최종 쇼츠 영상 파일 및 플랫폼별 메타데이터(제목, 태그).

5. 비기능적 요구사항 & 제약사항
비용 최적화: 이미지 및 비디오 API 호출 전 대본 컨펌 단계(Human-in-the-loop) 추가 기능.

확장성: 향후 Instagram, TikTok 외에 네이버 클립 등 추가 플랫폼 확장 고려.

속도: 전체 제작 공정(검색~렌더링)이 10분 이내에 완료될