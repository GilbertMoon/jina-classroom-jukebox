# Jina Classroom Jukebox

강의실에서 정해진 시간에 음악을 자동으로 재생하고, 학생의 신청곡과 관리자의 선곡·재생 제어를 지원하기 위한 학습 프로젝트입니다.

현재 단계는 **STEP 10: Ubuntu MPD 실제 재생 연결**입니다. 개발 환경에서는 모의 플레이어를 유지하고 강의실 서버에서 MPD를 선택할 수 있습니다.

## 지금 구현된 기능

- FastAPI 웹 서버
- 서버 안내 응답: `GET /`
- 서버 생존 상태 확인: `GET /health/live`
- Swagger API 문서: `GET /docs`
- 관리자 모의 플레이어 화면: `GET /admin`
- 플레이어 상태와 재생 제어 API
- 볼륨·음소거 제어
- SQLAlchemy 데이터 모델 9개
- Alembic 데이터베이스 마이그레이션
- PostgreSQL 연결 준비 상태 확인
- 반복 실행 가능한 개발용 예시 데이터
- 서명된 쿠키 세션을 사용하는 로그인·로그아웃
- 학생(`student`)과 관리자(`admin`) 역할 구분
- 관리자 제어 요청의 CSRF 방어와 감사 로그
- 학생용 신청곡 화면: `GET /student`
- YouTube 주소 검증·정규화와 중복 신청 차단
- 본인의 신청곡과 처리 상태만 조회
- 관리자의 전체 신청곡 조회와 승인·반려
- 반려 사유, 검토 관리자와 검토 시각 기록
- 승인된 곡의 음원 확보 대기 상태 전환과 감사 로그
- 승인된 곡의 MP3·OGG·FLAC 수동 업로드
- 파일 크기·내부 오디오 구조·재생 시간·SHA-256 중복 검사
- 이용 권한 확인 근거와 파일 메타데이터 저장
- 사용자 파일명 대신 곡 UUID로 안전하게 로컬 저장
- `READY` 곡 목록과 플레이리스트 조회
- 관리자 플레이리스트 생성·순서 저장·활성화
- 준비되지 않은 곡과 한 목록의 중복 곡 편성 차단
- 한 번에 하나의 플레이리스트만 활성화하고 변경 감사 로그 저장
- 요일·시작·종료 시간·볼륨별 자동 재생 스케줄
- 스케줄 겹침과 교차 자정 시간대 차단
- 서버 재시작 후 현재 시간대 자동 합류와 종료 시 자동 정지
- 재생 시작·종료 이력과 스케줄 변경 감사 로그
- 환경변수로 FakePlayer와 MPD 재생기 전환
- MPD 곡 목록 적재·재생·일시정지·정지·다음 곡·볼륨·음소거
- MPD 연결 상태 표시와 연결 실패 `503` 처리
- MPD 음악 폴더 밖의 파일 경로 차단과 스케줄 실패 기록
- pytest 자동 테스트
- GitHub Actions 자동 테스트

## 폴더 구조

```text
jina-classroom-jukebox/
├── .github/workflows/test.yml  # GitHub에서 자동으로 테스트하는 설정
├── backend/
│   ├── app/main.py             # FastAPI 서버가 시작되는 파일
│   ├── app/api/auth.py         # 로그인·로그아웃 API
│   ├── app/security.py         # 비밀번호 해시와 CSRF 토큰
│   ├── app/api/player.py       # 플레이어 제어 API
│   ├── app/api/song_requests.py # 신청곡 등록·조회 API
│   ├── app/api/media.py        # 권한 확인 음원 업로드 API
│   ├── app/api/tracks.py       # 재생 준비가 끝난 곡 조회 API
│   ├── app/api/playlists.py    # 플레이리스트 생성·편성·활성화 API
│   ├── app/api/schedules.py    # 자동 재생 스케줄 관리 API
│   ├── app/youtube.py          # YouTube 주소 검증·정규화
│   ├── app/services/media.py   # 오디오 파일 구조·재생 시간 검사
│   ├── app/services/player.py  # 메모리에서 동작하는 FakePlayer
│   ├── app/services/scheduler.py # 현재 시간 검사와 자동 재생 실행
│   ├── app/services/mpd_player.py # Ubuntu MPD 연결 어댑터
│   ├── app/templates/          # 관리자 HTML 화면
│   ├── app/static/             # 화면 CSS와 JavaScript
│   └── tests/test_main.py      # 서버와 플레이어를 확인하는 자동 테스트
├── migrations/                 # 데이터베이스 구조 변경 이력
├── deploy/mpd.conf.example     # localhost 전용 MPD 설정 예시
├── docs/ubuntu-mpd-setup.md    # Ubuntu 장비 연결 순서
├── scripts/seed_demo.py        # 개발용 예시 데이터 생성
├── alembic.ini                 # Alembic 설정
├── .env.example                # 환경변수 작성 예시(비밀값 없음)
├── .gitignore                  # GitHub에 올리지 않을 파일 목록
├── pytest.ini                  # pytest 설정
├── requirements.txt            # 서버 실행에 필요한 패키지
└── requirements-dev.txt        # 개발과 테스트에 필요한 패키지
```

## 처음 실행하기

아래 명령은 저장소의 최상위 폴더에서 실행합니다.

### 1. 가상환경 만들기

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Ubuntu/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

가상환경은 이 프로젝트만을 위한 독립된 Python 작업 공간입니다. 다른 프로젝트의 패키지와 섞이는 것을 막아줍니다.

### 2. 패키지 설치하기

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

### 3. 자동 테스트 실행하기

```bash
pytest
```

`41 passed`가 표시되면 서버, 로그인, 신청·음원·플레이리스트·스케줄과 Fake/MPD 재생 API가 정상이라는 뜻입니다.

### 4. 개발 서버 실행하기

```bash
python -m uvicorn backend.app.main:app --reload
```

브라우저에서 다음 주소를 확인합니다.

- 홈: <http://127.0.0.1:8000/>
- 상태 확인: <http://127.0.0.1:8000/health/live>
- DB 준비 상태: <http://127.0.0.1:8000/health/ready>
- API 문서: <http://127.0.0.1:8000/docs>
- 로그인: <http://127.0.0.1:8000/login>
- 학생 신청곡: <http://127.0.0.1:8000/student>
- 관리자 모의 플레이어: <http://127.0.0.1:8000/admin>

서버를 종료하려면 터미널에서 `Ctrl+C`를 누릅니다.

## 환경변수

`.env.example`을 복사하여 `.env`를 만듭니다. `.env`는 비밀정보가 들어갈 수 있으므로 Git에 저장하지 않습니다.

```powershell
Copy-Item .env.example .env
```

다음 값은 반드시 본인만 아는 값으로 바꿉니다.

- `SESSION_SECRET`: 로그인 쿠키의 위조 여부를 확인하는 긴 무작위 문자열
- `DEMO_ADMIN_PASSWORD`: 개발용 관리자 비밀번호
- `DEMO_STUDENT_PASSWORD`: 개발용 학생 비밀번호
- `MEDIA_ROOT`: 권한이 확인된 음원 파일을 저장할 비공개 폴더
- `MAX_MEDIA_SIZE_MB`: 음원 파일 하나의 최대 크기(MB, 기본 50)
- `SCHEDULER_ENABLED`: 자동 스케줄 실행 여부(`true` 또는 `false`)
- `SCHEDULER_INTERVAL_SECONDS`: 현재 시간 확인 간격(기본 30초, 최소 5초)
- `PLAYER_BACKEND`: 개발용 `fake` 또는 실제 장비용 `mpd`
- `MPD_HOST`, `MPD_PORT`: MPD 연결 주소와 포트
- `MPD_PASSWORD`: MPD에 비밀번호를 설정한 경우에만 입력
- `MPD_TIMEOUT_SECONDS`: 연결·음악 DB 갱신 제한 시간
- `MPD_MUSIC_ROOT`: MPD의 `music_directory`와 같은 절대 경로

## PostgreSQL 데이터베이스 준비

먼저 PostgreSQL에 `jukebox` 데이터베이스와 전용 사용자를 준비합니다. 실제 비밀번호는 `.env`의 `DATABASE_URL`에만 작성하고 GitHub에는 올리지 않습니다.

PowerShell에서 현재 터미널에 연결 주소를 설정하는 예시입니다.

```powershell
$env:DATABASE_URL="postgresql+psycopg://jukebox:실제비밀번호@localhost:5432/jukebox"
```

Ubuntu/macOS 예시입니다.

```bash
export DATABASE_URL="postgresql+psycopg://jukebox:실제비밀번호@localhost:5432/jukebox"
```

데이터베이스 테이블을 최신 구조로 만듭니다.

```bash
python -m alembic upgrade head
```

현재 마이그레이션 버전을 확인하려면 다음 명령을 사용합니다.

```bash
python -m alembic current
```

개발용 계정과 테스트 곡 메타데이터를 한 번 넣으려면 다음 명령을 사용합니다. 여러 번 실행해도 같은 데이터가 중복 생성되지 않습니다.

```bash
python -m scripts.seed_demo
```

개발용 로그인 이메일은 아래와 같습니다. 비밀번호는 `.env`에 직접 지정한 값을 사용합니다.

- 관리자: `admin@jukebox.local`
- 학생: `student@jukebox.local`

비밀번호 원문은 데이터베이스에 저장하지 않습니다. Argon2로 만든 해시만 저장하므로, 데이터베이스를 보더라도 원래 비밀번호가 그대로 노출되지 않습니다.

## STEP 04가 동작하는 순서

1. 사용자가 이메일과 비밀번호를 입력합니다.
2. 서버가 저장된 Argon2 해시와 비밀번호를 비교합니다.
3. 성공하면 서버가 서명된 세션 쿠키를 브라우저에 보냅니다.
4. 이후 요청마다 서버가 세션의 사용자와 역할을 다시 확인합니다.
5. 학생은 플레이어 상태를 볼 수 있지만 재생·볼륨 제어는 할 수 없습니다.
6. 관리자의 변경 요청에는 CSRF 토큰이 필요하며, 누가 무엇을 변경했는지 감사 로그로 남깁니다.

세션 쿠키는 출입증, 역할은 출입증에 적힌 권한이라고 생각하면 쉽습니다. CSRF 토큰은 다른 사이트가 사용자를 속여 버튼을 누르게 하는 요청을 막는 추가 확인표입니다.

## STEP 05가 동작하는 순서

1. 학생이 로그인하면 `/student` 신청곡 화면으로 이동합니다.
2. YouTube 주소, 곡 제목, 가수·채널과 선택 메모를 입력합니다.
3. 서버가 공식 YouTube 주소인지 확인하고 11자리 영상 ID를 추출합니다.
4. 같은 영상은 하나의 `tracks` 곡 정보로 관리하고, 학생의 신청은 `requests`에 따로 저장합니다.
5. 같은 학생이 같은 영상을 다시 신청하면 중복임을 알려줍니다.
6. 학생은 `/api/requests/me`를 통해 본인의 신청 내역만 볼 수 있습니다.

`Track`은 도서관의 책 정보, `SongRequest`는 “누가 그 책을 신청했는지” 적은 신청서라고 생각하면 쉽습니다. YouTube 주소는 검색·식별·검토에만 사용하며 이 단계에서는 음원을 내려받지 않습니다.

## STEP 06이 동작하는 순서

1. 관리자가 `/admin`의 신청곡 승인함을 엽니다.
2. `GET /api/requests`가 신청자와 곡 정보를 불러옵니다.
3. 관리자가 승인 또는 반려를 선택합니다.
4. 반려할 때는 사유를 반드시 입력합니다.
5. `POST /api/requests/{id}/review`가 관리자 권한과 CSRF 토큰을 검사합니다.
6. 승인하면 신청은 `APPROVED`, 곡은 `PENDING_ACQUISITION`으로 바뀝니다.
7. 반려하면 신청은 `REJECTED`가 되고 학생 화면에 반려 사유가 표시됩니다.
8. 처리한 관리자, 처리 시각과 감사 로그를 함께 저장합니다.

상태는 결재 문서의 도장과 비슷합니다. 처음에는 `PENDING`이고 한 번 승인 또는 반려된 신청은 다시 처리할 수 없도록 서버가 막습니다.

## STEP 07이 동작하는 순서

1. 관리자가 신청곡을 승인하면 곡은 `PENDING_ACQUISITION` 상태가 됩니다.
2. 관리자 승인함에서 MP3, OGG 또는 FLAC 파일을 선택합니다.
3. 파일을 저장하고 재생할 권리가 있다는 확인과 근거를 입력합니다.
4. `POST /api/media/upload`가 관리자 권한과 CSRF 토큰을 확인합니다.
5. 서버가 확장자, 최대 크기, 실제 오디오 구조와 재생 시간을 검사합니다.
6. SHA-256 해시로 이미 등록된 동일 파일인지 확인합니다.
7. 통과한 파일은 사용자 파일명이 아닌 `<track-id>.<확장자>`로 `MEDIA_ROOT`에 저장됩니다.
8. 곡 상태가 `READY`가 되고 파일 정보와 관리자 감사 로그가 저장됩니다.

`APPROVED`는 “이 신청을 받아들였다”는 뜻이고, `READY`는 “권한과 파일 검사가 끝나 실제 재생 준비가 됐다”는 뜻입니다. 두 상태는 서로 다릅니다. 이 단계는 YouTube 영상을 다운로드하거나 변환하지 않습니다.

## STEP 08이 동작하는 순서

1. `GET /api/tracks`가 파일 검사를 통과한 `READY` 곡만 보여줍니다.
2. 관리자가 `/admin`의 플레이리스트 편성 영역에서 새 목록을 만듭니다.
3. 원하는 곡을 추가하고 위·아래 버튼으로 재생 순서를 정합니다.
4. `PUT /api/playlists/{id}/items`가 순서를 1번부터 다시 저장합니다.
5. 서버는 모든 곡이 `READY`인지, 같은 곡이 중복됐는지 다시 검사합니다.
6. `POST /api/playlists/{id}/activate`로 운영에 사용할 목록을 활성화합니다.
7. 새 목록을 활성화하면 이전 활성 목록은 자동으로 비활성화됩니다.
8. 생성·편성·활성화 작업은 관리자 감사 로그에 저장됩니다.

`Playlist`는 재생 목록의 이름표이고, `PlaylistItem.position`은 각 곡 앞에 붙는 순번입니다. 화면에서 순서를 바꾸더라도 최종 검사는 항상 서버가 수행합니다.

## STEP 09가 동작하는 순서

1. 관리자가 활성 플레이리스트, 요일, 시작·종료 시간과 볼륨을 선택합니다.
2. `POST /api/schedules`가 교차 자정과 기존 스케줄 겹침을 검사합니다.
3. APScheduler가 기본 30초마다 현재 `Asia/Seoul` 시간을 확인합니다.
4. 재생 시간대에 들어오면 플레이리스트를 모의 플레이어에 싣고 지정 볼륨으로 재생합니다.
5. 서버가 시간대 중간에 재시작되어도 다음 검사에서 해당 스케줄에 합류합니다.
6. 종료 시간이 되거나 플레이리스트·스케줄이 비활성화되면 자동으로 정지합니다.
7. 시작·종료는 `playback_events`, 설정 변경은 관리자 감사 로그에 저장합니다.

스케줄은 알람시계와 비슷합니다. 데이터베이스에는 “언제 무엇을 틀지”를 저장하고, APScheduler는 주기적으로 시계를 보며 시작과 종료 명령을 실행합니다. 같은 앱을 여러 프로세스로 실행하면 명령이 중복될 수 있으므로 현재 단계에서는 Uvicorn 작업자 1개로 실행합니다.

## STEP 10이 동작하는 순서

1. 서버 시작 시 `PLAYER_BACKEND`를 읽습니다.
2. `fake`이면 메모리 속 모의 플레이어, `mpd`이면 Ubuntu의 MPD에 연결합니다.
3. 스케줄이 시작되면 DB의 플레이리스트 파일 경로를 MPD 음악 폴더 기준 상대 경로로 변환합니다.
4. MPD 음악 데이터베이스를 갱신하고 곡 순서대로 대기열에 넣습니다.
5. 기존 플레이어 API가 MPD의 재생·정지·다음 곡·볼륨을 제어합니다.
6. 대시보드는 5초마다 상태를 읽어 `MPD Online` 또는 `MPD Offline`을 표시합니다.
7. 연결 실패 시 제어 API는 `503`, 자동 스케줄은 `FAILED` 재생 이력을 남깁니다.

애플리케이션은 리모컨이고 MPD는 실제 오디오 장치를 다루는 재생기라고 생각하면 쉽습니다. [`Ubuntu MPD 연결 안내`](docs/ubuntu-mpd-setup.md)를 따라 장비를 준비하세요. `MEDIA_ROOT`와 `MPD_MUSIC_ROOT`는 반드시 같은 폴더를 가리켜야 합니다.

`GET /health/live`는 웹 프로세스가 살아 있는지만 확인합니다. `GET /health/ready`는 PostgreSQL 연결까지 성공해야 `200`을 반환합니다. DB가 연결되지 않으면 안전하게 `503`을 반환합니다.

GitHub Actions에서는 별도의 PostgreSQL 18.6 서비스를 실행하여 마이그레이션과 예시 데이터 생성을 실제 PostgreSQL에서도 자동 검증합니다.

## 안전한 저장소 사용 원칙

- 비밀번호, API 키, 데이터베이스 접속정보를 커밋하지 않습니다.
- 음악 파일과 데이터베이스 덤프를 커밋하지 않습니다.
- YouTube URL은 곡 검색·식별·검토 용도로 사용합니다.
- 실제 음원은 사용 권한이 확인된 파일만 등록합니다.

## 다음 단계

STEP 11에서는 서버·MPD·오디오 장치 장애 상태와 운영 기록을 한 화면에서 확인하도록 개선합니다.
