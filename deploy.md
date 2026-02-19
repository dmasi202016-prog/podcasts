# 배포 가이드: Railway + Vercel + Supabase

팟캐스트 쇼츠 플랫폼을 외부 접근 가능한 환경으로 배포하는 가이드입니다.

| 구성 요소 | 배포 대상 |
|----------|----------|
| 백엔드 (FastAPI) | **Railway** |
| 프론트엔드 (Next.js) | **Vercel** |
| 미디어 파일 저장 | **Supabase Storage** |
| 결과 메타데이터 DB | **Supabase PostgreSQL** |

---

## 1. Supabase 프로젝트 설정

### 1-1. 프로젝트 생성
1. https://supabase.com 에서 **New Project** 생성
2. **Project Settings → API** 에서 확인:
   - `SUPABASE_URL`: `https://xxx.supabase.co`
   - `SUPABASE_SERVICE_ROLE_KEY`: `eyJ...` (비공개 유지!)
3. **Project Settings → Database** 에서 확인:
   - `DATABASE_URL`: `postgresql://postgres.xxx:password@aws-0-...pooler.supabase.com:6543/postgres`
   - **Transaction mode** (port 6543) 사용 권장

### 1-2. Storage Bucket 생성
1. Storage 메뉴 → **New Bucket**
2. 이름: `pipeline-outputs`
3. **Public** 체크
4. File size limit: `500MB`
5. Allowed MIME types: 비워두기 (모두 허용)

### 1-3. Database 테이블 생성
SQL Editor에서 실행:

```sql
CREATE TABLE pipeline_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'started',
    final_video_url TEXT,
    caption_srt_url TEXT,
    thumbnail_url TEXT,
    title TEXT,
    description TEXT,
    tags TEXT[],
    category TEXT,
    duration_sec FLOAT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_pipeline_runs_run_id ON pipeline_runs(run_id);
CREATE INDEX idx_pipeline_runs_user_id ON pipeline_runs(user_id);
```

### 1-4. Storage RLS 정책
```sql
-- 누구나 읽기 허용
CREATE POLICY "public_read" ON storage.objects
  FOR SELECT USING (bucket_id = 'pipeline-outputs');

-- service_role로만 업로드
CREATE POLICY "service_upload" ON storage.objects
  FOR INSERT WITH CHECK (bucket_id = 'pipeline-outputs');
```

---

## 2. Railway 배포 (백엔드)

### 2-1. Railway 프로젝트 생성
1. https://railway.app 에서 **New Project → Deploy from GitHub repo** 선택
2. `podcast-shorts` 디렉토리를 루트로 설정
3. Railway가 `Dockerfile`을 자동 감지하여 빌드

### 2-2. 환경변수 설정

Railway Dashboard → Variables에 아래 환경변수 추가:

```env
# LLM & API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
TAVILY_API_KEY=tvly-...
YOUTUBE_API_KEY=AIza...
TWITTER_BEARER_TOKEN=AAAA...
ELEVENLABS_API_KEY=...
LUMA_API_KEY=luma-...

# Voice IDs (모든 가족 구성원)
VOICE_ID_ME=...
VOICE_ID_WIFE=...
VOICE_ID_JIHO=...
VOICE_ID_JIHYUNG=...
VOICE_ID_JIWON=...
VOICE_ID_GRANDFA=...
VOICE_ID_GRANDMA=...
VOICE_ID_UNHA=...

# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
DATABASE_URL=postgresql://postgres.xxx:password@aws-0-...pooler.supabase.com:6543/postgres

# Deployment
ALLOWED_ORIGINS=https://xxx.vercel.app
CHECKPOINT_BACKEND=postgres
```

### 2-3. 배포 확인
```bash
# Health check
curl https://xxx.up.railway.app/health
# 응답: {"status": "ok"}
```

---

## 3. Vercel 배포 (프론트엔드)

### 3-1. Vercel 프로젝트 생성
1. https://vercel.com 에서 **Import Git Repository**
2. `podcast-shorts-frontend` 디렉토리를 Root Directory로 설정
3. Framework Preset: **Next.js** (자동 감지)

### 3-2. 환경변수 설정

Vercel Dashboard → Settings → Environment Variables:

```env
NEXT_PUBLIC_API_URL=https://xxx.up.railway.app
NEXT_PUBLIC_FILES_URL=https://xxx.up.railway.app/files
```

### 3-3. 배포 확인
Vercel에서 제공하는 URL로 접속하여 프론트엔드가 정상 동작하는지 확인.

---

## 4. 로컬 개발 (기존 방식 유지)

Supabase 환경변수 없이 실행하면 기존과 동일하게 동작합니다:

- `upload_results` 노드가 자동 skip
- InMemorySaver 체크포인터 사용
- 로컬 파일 시스템에 output 저장

```bash
# 백엔드
cd podcast-shorts
uvicorn podcast_shorts.main:app --reload --port 8000

# 프론트엔드
cd podcast-shorts-frontend
npm run dev
```

로컬에서 Supabase 연동 테스트를 원하면 `.env`에 아래 추가:
```env
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
DATABASE_URL=postgresql://...
CHECKPOINT_BACKEND=postgres
```

---

## 5. 검증 체크리스트

- [ ] **로컬 테스트**: Supabase env 없이 기존처럼 동작 확인 (upload_results skip)
- [ ] **Supabase 연동**: `.env`에 Supabase 설정 후 파이프라인 실행 → Storage에 파일 업로드 + DB 행 생성 확인
- [ ] **Railway 배포**: Docker build 성공, `/health` 응답, 파이프라인 end-to-end
- [ ] **Vercel 배포**: 프론트엔드에서 Railway API 호출, Supabase URL로 영상 재생/다운로드
- [ ] **서버 재시작 후**: Railway 재시작 후 `/result` API가 DB fallback으로 이전 결과 반환 확인

---

## 아키텍처 다이어그램

```
┌──────────────┐     HTTPS     ┌──────────────────┐
│   Vercel     │ ────────────> │   Railway        │
│  (Next.js)   │               │  (FastAPI)       │
└──────┬───────┘               └──────┬───────────┘
       │                              │
       │  Supabase public URL         │  service_role key
       │                              │
       └──────────┐    ┌──────────────┘
                  ▼    ▼
           ┌─────────────────┐
           │    Supabase     │
           │  ┌───────────┐  │
           │  │  Storage   │  │  ← 동영상, SRT, 썸네일
           │  └───────────┘  │
           │  ┌───────────┐  │
           │  │ PostgreSQL │  │  ← pipeline_runs 메타데이터
           │  └───────────┘  │
           └─────────────────┘
```
