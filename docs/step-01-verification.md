# STEP 01 검증 기록

이 문서는 프로젝트 기반과 FastAPI 개발 환경이 STEP 01 완료 기준을 충족하는지 확인한 결과입니다.

## 확인 결과

| 완료 기준 | 확인 방법 | 결과 |
|---|---|---|
| 기본 디렉터리 구성 | 저장소의 `backend`, `docs`, `scripts`, `.github` 구조 확인 | 통과 |
| Python 가상환경과 의존성 | `.venv`, `requirements.txt`, `requirements-dev.txt` 확인 | 통과 |
| FastAPI 애플리케이션 | `backend.app.main:app` 로딩 및 자동 테스트 | 통과 |
| 서버 생존 상태 | `GET /health/live`가 HTTP 200인지 자동 테스트 | 통과 |
| Swagger API 문서 | `GET /docs`가 HTTP 200이고 Swagger UI를 반환하는지 자동 테스트 | 통과 |
| 환경 설정 예시 | `.env.example`에 실행·DB·세션·스케줄·MPD 설정이 있는지 확인 | 통과 |
| 초보자 실행 안내 | README의 가상환경, 설치, 테스트, 서버 실행 순서 확인 | 통과 |
| 자동 테스트 | 로컬 pytest 전체 실행 | 통과 |
| 지속적 통합 | `.github/workflows/test.yml`의 PostgreSQL·마이그레이션·pytest 작업 확인 | 통과 |

## 실행 명령

저장소 최상위 폴더에서 다음 명령을 실행합니다.

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m alembic heads
.\.venv\Scripts\python.exe -m compileall -q backend
```

## 검증 결과

- pytest: 42개 테스트 통과
- Alembic: `0004`가 최신 head
- Python 컴파일 검사: 통과
- Git 공백 오류 검사: 통과

Windows의 제한된 실행 환경에서 pytest 기본 임시폴더를 만들 수 없는 경우에는 쓰기 가능한 폴더를 지정합니다.

```powershell
.\.venv\Scripts\python.exe -m pytest --basetemp=.pytest-tmp
```

`.pytest-tmp`는 검사 중에만 사용하는 임시폴더이며 프로젝트 기능에는 영향을 주지 않습니다.
