# Ubuntu MPD 연결 안내

이 문서는 실제 강의실 Ubuntu 서버에서만 진행합니다. 개발 PC에서는 `.env`의 `PLAYER_BACKEND=fake`를 유지하세요.

## 1. MPD와 확인 도구 설치

```bash
sudo apt update
sudo apt install mpd mpc alsa-utils
```

오디오 장치가 보이는지 먼저 확인합니다.

```bash
aplay -l
```

## 2. 음원 폴더 준비

예시 저장 위치는 `/srv/ax2-jukebox/media`입니다. FastAPI를 실행하는 계정은 파일을 쓸 수 있고, `mpd` 계정은 읽을 수 있어야 합니다. 서버의 실제 계정과 보안 정책에 맞게 소유자와 그룹을 정하세요.

```bash
sudo mkdir -p /srv/ax2-jukebox/media
sudo chgrp -R audio /srv/ax2-jukebox/media
sudo chmod 2770 /srv/ax2-jukebox/media
```

FastAPI 실행 계정도 `audio` 그룹에 추가한 뒤 다시 로그인해야 합니다.

```bash
sudo usermod -aG audio <FastAPI를 실행하는 계정>
```

## 3. MPD 설정

[`deploy/mpd.conf.example`](../deploy/mpd.conf.example)을 참고하여 `/etc/mpd.conf`의 음악 폴더와 오디오 출력을 설정합니다. USB DAC 또는 HDMI를 사용한다면 `device` 값을 `aplay -l` 결과에 맞게 바꿔야 할 수 있습니다.

MPD 포트 `6600`은 외부에 공개하지 말고 `127.0.0.1`에서만 수신하도록 유지합니다.

```bash
sudo systemctl restart mpd
sudo systemctl enable mpd
sudo systemctl status mpd
```

## 4. MPD 단독 확인

권한이 확인된 테스트 음원 하나를 음악 폴더에 넣은 다음 데이터베이스를 갱신합니다.

```bash
mpc update
mpc listall
mpc add <표시된 상대 경로>
mpc play
mpc status
```

소리가 나오지 않으면 먼저 `mpc status`, `journalctl -u mpd`, `aplay -l`을 확인합니다. 웹 애플리케이션 문제와 오디오 장치 문제를 분리해서 확인하는 과정입니다.

## 5. 애플리케이션 연결

프로젝트 `.env`에서 두 음악 폴더를 같은 실제 위치로 지정합니다.

```env
PLAYER_BACKEND=mpd
MEDIA_ROOT=/srv/ax2-jukebox/media
MPD_MUSIC_ROOT=/srv/ax2-jukebox/media
MPD_HOST=127.0.0.1
MPD_PORT=6600
MPD_PASSWORD=
MPD_TIMEOUT_SECONDS=5
```

서버를 다시 시작하고 관리자 화면 상단에 `MPD Online`이 표시되는지 확인합니다. 연결되지 않으면 `MPD Offline`과 `503` 응답이 표시되며 스케줄 실패는 재생 이력에 기록됩니다.

## 6. fake 모드로 되돌리기

장비 없이 개발하거나 장애를 진단할 때는 다음 값으로 되돌립니다.

```env
PLAYER_BACKEND=fake
```

환경변수를 바꾼 뒤에는 FastAPI 서버를 다시 시작해야 합니다.
