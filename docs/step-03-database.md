# STEP 03: PostgreSQL과 Alembic 이해하기

이 단계의 목표는 서버를 껐다 켜도 사용자, 곡, 신청곡, 플레이리스트와
스케줄이 사라지지 않도록 PostgreSQL에 저장하는 것입니다.

## 세 가지 구성요소

- **PostgreSQL**: 실제 데이터를 보관하는 창고입니다.
- **SQLAlchemy 모델**: Python 코드에서 데이터의 모양과 관계를 표현합니다.
- **Alembic 마이그레이션**: 데이터베이스 구조의 변경 이력을 순서대로 적용합니다.

모델만 수정하면 이미 만들어진 데이터베이스는 자동으로 바뀌지 않습니다.
모델 변경과 Alembic 마이그레이션을 항상 함께 작성해야 합니다.

## 1. 환경변수 준비

`.env.example`을 `.env`로 복사하고 `DATABASE_URL`의 비밀번호를 실제 값으로
바꿉니다. `.env`는 Git에 커밋하지 않습니다.

```powershell
Copy-Item .env.example .env
```

연결 주소의 각 부분은 다음 뜻입니다.

```text
postgresql+psycopg://사용자:비밀번호@서버주소:5432/데이터베이스이름
```

## 2. 마이그레이션 적용

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current
```

`upgrade head`는 아직 적용하지 않은 변경을 최신 버전까지 적용합니다.
`current`는 현재 적용된 버전을 보여줍니다.

## 3. 개발용 데이터 넣기

```powershell
.\.venv\Scripts\python.exe -m scripts.seed_demo
```

이 명령은 여러 번 실행해도 동일한 사용자와 곡을 중복 생성하지 않습니다.

## 4. 롤백 확인

개발용 빈 데이터베이스에서만 다음 명령을 실행합니다.

```powershell
.\.venv\Scripts\python.exe -m alembic downgrade -1
.\.venv\Scripts\python.exe -m alembic upgrade head
```

`downgrade -1`은 바로 이전 마이그레이션으로 한 단계 되돌립니다. 운영 데이터가
있는 데이터베이스에서는 데이터 손실 가능성이 있으므로 임의로 실행하지 않습니다.

## 저장되는 핵심 테이블

- `users`, `tracks`, `requests`: 사용자, 곡, 신청 내역
- `playlists`, `playlist_items`: 재생 목록과 순서
- `schedules`: 자동 재생 시간표
- `playback_events`, `control_audit_logs`: 재생·관리자 작업 이력
- `system_settings`: 시스템 설정

## 데이터베이스가 막아 주는 잘못된 값

API 검증을 우회한 요청이 들어와도 데이터베이스가 마지막으로 데이터를 보호합니다.

- 곡 길이와 파일 크기는 음수가 될 수 없습니다.
- 플레이리스트 순번은 1부터 시작합니다.
- 스케줄 볼륨은 0부터 100 사이입니다.
- 스케줄 종료 시간은 시작 시간보다 뒤여야 합니다.
- 재생 종료 시각은 시작 시각보다 빠를 수 없습니다.

## 완료 확인

1. 빈 DB에서 `alembic upgrade head`가 성공합니다.
2. `python -m scripts.seed_demo`를 두 번 실행해도 중복이 없습니다.
3. 서버를 재시작한 뒤에도 데이터가 조회됩니다.
4. `alembic downgrade -1` 후 `upgrade head`가 다시 성공합니다.
5. `pytest`가 모두 통과합니다.

데이터베이스 연결이 끊기면 `GET /health/ready`는 `503`을 반환합니다. 웹 서버가
살아 있는지와 데이터베이스까지 준비됐는지를 구분할 수 있어 운영자가 원인을
명확하게 확인할 수 있습니다.
