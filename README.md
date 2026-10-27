# Jina Classroom Jukebox

강의실에서 정해진 시간에 음악을 자동으로 재생하고, 학생의 신청곡과 관리자의 선곡·재생 제어를 지원하기 위한 학습 프로젝트입니다.

현재 단계는 **STEP 03: PostgreSQL 데이터베이스 기반**입니다. 아직 실제 음악 재생이나 로그인 기능은 포함하지 않습니다.

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
- pytest 자동 테스트
- GitHub Actions 자동 테스트

## 폴더 구조

```text
jina-classroom-jukebox/
├── .github/workflows/test.yml  # GitHub에서 자동으로 테스트하는 설정
├── backend/
│   ├── app/main.py             # FastAPI 서버가 시작되는 파일
│   ├── app/api/player.py       # 플레이어 제어 API
│   ├── app/services/player.py  # 메모리에서 동작하는 FakePlayer
│   ├── app/templates/          # 관리자 HTML 화면
│   ├── app/static/             # 화면 CSS와 JavaScript
│   └── tests/test_main.py      # 서버와 플레이어를 확인하는 자동 테스트
├── migrations/                 # 데이터베이스 구조 변경 이력
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

`7 passed`가 표시되면 서버, 관리자 화면과 모의 플레이어 API가 정상이라는 뜻입니다.

### 4. 개발 서버 실행하기

```bash
python -m uvicorn backend.app.main:app --reload
```

브라우저에서 다음 주소를 확인합니다.

- 홈: <http://127.0.0.1:8000/>
- 상태 확인: <http://127.0.0.1:8000/health/live>
- DB 준비 상태: <http://127.0.0.1:8000/health/ready>
- API 문서: <http://127.0.0.1:8000/docs>
- 관리자 모의 플레이어: <http://127.0.0.1:8000/admin>

서버를 종료하려면 터미널에서 `Ctrl+C`를 누릅니다.

## 환경변수

개발용 환경변수 파일이 필요해지면 `.env.example`을 복사하여 `.env`를 만듭니다. `.env`는 비밀정보가 들어갈 수 있으므로 Git에 저장하지 않습니다.

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

개발용 관리자와 테스트 곡 메타데이터를 한 번 넣으려면 다음 명령을 사용합니다. 여러 번 실행해도 같은 데이터가 중복 생성되지 않습니다.

```bash
python -m scripts.seed_demo
```

`GET /health/live`는 웹 프로세스가 살아 있는지만 확인합니다. `GET /health/ready`는 PostgreSQL 연결까지 성공해야 `200`을 반환합니다. DB가 연결되지 않으면 안전하게 `503`을 반환합니다.

GitHub Actions에서는 별도의 PostgreSQL 18.6 서비스를 실행하여 마이그레이션과 예시 데이터 생성을 실제 PostgreSQL에서도 자동 검증합니다.

## 안전한 저장소 사용 원칙

- 비밀번호, API 키, 데이터베이스 접속정보를 커밋하지 않습니다.
- 음악 파일과 데이터베이스 덤프를 커밋하지 않습니다.
- YouTube URL은 곡 검색·식별·검토 용도로 사용합니다.
- 실제 음원은 사용 권한이 확인된 파일만 등록합니다.

## 다음 단계

STEP 04에서는 로그인과 학생·관리자 권한을 구현합니다.
