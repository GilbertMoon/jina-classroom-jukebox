# STEP 05 신청곡·Wish List 규칙

## 기존 구조 재사용

- 로그인 세션에서 학생 ID를 가져오며 요청 본문의 학생 ID는 신뢰하지 않습니다.
- 기존 `tracks`, `requests` 테이블과 관리자 승인 API를 그대로 사용합니다.
- Wish List에 필요한 `wish_list_items` 테이블만 추가합니다.

## 지원하는 YouTube 주소

- `youtube.com/watch?v=<11자리 video ID>`
- `youtu.be/<11자리 video ID>`
- `youtube.com/shorts/<11자리 video ID>`
- `youtube.com/embed/<11자리 video ID>`

호스트와 11자리 video ID를 모두 검사합니다. 지원하지 않거나 잘못된 주소에는
`422`와 사용자용 안내 문구를 반환합니다. 음원 다운로드는 하지 않습니다.

## 신청 상태와 재신청

| 현재 상태 | 같은 학생·video ID 재신청 | 취소 |
|---|---|---|
| `PENDING` | 불가 | 가능 |
| `APPROVED` | 불가 | 불가 |
| `REJECTED` | 가능하며 기존 건을 `PENDING`으로 되돌림 | 불가 |

취소와 Wish List 삭제는 로그인한 학생 소유의 항목에만 허용합니다. 다른 학생의
UUID를 사용하면 존재 여부를 드러내지 않도록 `404`를 반환합니다.

## Wish List 전환

- 같은 학생·트랙 조합은 한 번만 저장할 수 있습니다.
- 신청 전환 시 기존 신청 상태 규칙을 똑같이 적용합니다.
- 전환이 성공하면 해당 항목은 Wish List에서 제거됩니다.
- 신청이 중복되어 실패하면 Wish List 항목은 유지됩니다.
