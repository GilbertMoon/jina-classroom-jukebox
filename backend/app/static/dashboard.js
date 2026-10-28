const stateLabels = {
  stopped: ["정지", "text-bg-secondary"],
  playing: ["재생 중", "text-bg-success"],
  paused: ["일시정지", "text-bg-warning"],
};

const csrfToken = document.querySelector('meta[name="csrf-token"]').content;

const elements = {
  alert: document.querySelector("#alert"),
  stateBadge: document.querySelector("#state-badge"),
  trackTitle: document.querySelector("#track-title"),
  trackArtist: document.querySelector("#track-artist"),
  trackProgress: document.querySelector("#track-progress"),
  elapsedTime: document.querySelector("#elapsed-time"),
  durationTime: document.querySelector("#duration-time"),
  nextTitle: document.querySelector("#next-title"),
  nextArtist: document.querySelector("#next-artist"),
  volume: document.querySelector("#volume"),
  volumeValue: document.querySelector("#volume-value"),
  muteButton: document.querySelector("#mute-button"),
  logoutButton: document.querySelector("#logout-button"),
  reviewList: document.querySelector("#review-list"),
  reviewRefreshButton: document.querySelector("#review-refresh-button"),
};

function formatTime(seconds) {
  const minutes = Math.floor(seconds / 60);
  return `${minutes}:${String(seconds % 60).padStart(2, "0")}`;
}

function render(state) {
  const [label, badgeClass] = stateLabels[state.playback_state];
  elements.stateBadge.className = `badge ${badgeClass}`;
  elements.stateBadge.textContent = label;
  elements.trackTitle.textContent = state.current_track.title;
  elements.trackArtist.textContent = state.current_track.artist;
  elements.nextTitle.textContent = state.next_track.title;
  elements.nextArtist.textContent = state.next_track.artist;
  elements.elapsedTime.textContent = formatTime(state.progress_seconds);
  elements.durationTime.textContent = formatTime(state.current_track.duration_seconds);

  const progress = state.current_track.duration_seconds
    ? (state.progress_seconds / state.current_track.duration_seconds) * 100
    : 0;
  elements.trackProgress.style.width = `${progress}%`;

  elements.volume.value = state.volume;
  elements.volumeValue.textContent = `${state.volume}%`;
  elements.muteButton.textContent = state.muted ? "음소거 해제" : "음소거";
  elements.muteButton.setAttribute("aria-pressed", String(state.muted));
  elements.muteButton.classList.toggle("btn-info", state.muted);
  elements.muteButton.classList.toggle("btn-outline-info", !state.muted);
}

function showError(error) {
  elements.alert.textContent = `플레이어 요청에 실패했습니다: ${error.message}`;
  elements.alert.classList.remove("d-none");
}

async function request(url, options = {}) {
  elements.alert.classList.add("d-none");
  const isFormData = options.body instanceof FormData;
  const response = await fetch(url, {
    ...options,
    headers: {
      ...(!isFormData ? { "Content-Type": "application/json" } : {}),
      ...(options.method && options.method !== "GET" ? { "X-CSRF-Token": csrfToken } : {}),
      ...options.headers,
    },
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || `HTTP ${response.status}`);
  }
  return response.json();
}

const reviewStatusLabels = {
  PENDING: "승인 대기",
  APPROVED: "승인",
  REJECTED: "반려",
};

function makeText(tagName, className, text) {
  const element = document.createElement(tagName);
  element.className = className;
  element.textContent = text;
  return element;
}

function renderReviewList(items) {
  if (!items.length) {
    elements.reviewList.innerHTML = '<p class="text-secondary mb-0">접수된 신청곡이 없습니다.</p>';
    return;
  }

  elements.reviewList.replaceChildren(...items.map((item) => {
    const article = document.createElement("article");
    article.className = "request-item border rounded-3 p-3";

    const header = document.createElement("div");
    header.className = "d-flex flex-wrap justify-content-between gap-3";
    const details = document.createElement("div");
    details.append(
      makeText("h3", "h6 fw-bold mb-1", item.title),
      makeText("p", "small text-secondary mb-1", item.artist_or_channel || "가수·채널 미입력"),
      makeText("p", "small mb-2", `신청자: ${item.requester_name} (${item.requester_email})`),
    );
    const link = document.createElement("a");
    link.href = item.youtube_url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.className = "small";
    link.textContent = "YouTube에서 검토";
    details.append(link);
    const badge = makeText("span", `badge request-status-${item.status.toLowerCase()}`, reviewStatusLabels[item.status] || item.status);
    header.append(details, badge);
    article.append(header);

    if (item.comment) article.append(makeText("p", "small mt-3 mb-0", `학생 메모: ${item.comment}`));
    if (item.reject_reason) article.append(makeText("p", "small text-danger mt-2 mb-0", `반려 사유: ${item.reject_reason}`));

    if (item.status === "PENDING") {
      const controls = document.createElement("div");
      controls.className = "d-flex flex-wrap gap-2 mt-3";
      const approve = makeText("button", "btn btn-sm btn-success", "승인");
      approve.type = "button";
      approve.addEventListener("click", () => reviewRequest(item.id, "APPROVE"));
      const reject = makeText("button", "btn btn-sm btn-outline-danger", "반려");
      reject.type = "button";
      reject.addEventListener("click", () => {
        const reason = window.prompt("반려 사유를 입력해 주세요.");
        if (reason !== null) reviewRequest(item.id, "REJECT", reason);
      });
      controls.append(approve, reject);
      article.append(controls);
    }

    if (item.status === "APPROVED" && item.media_status !== "READY") {
      article.append(createMediaUploadForm(item));
    } else if (item.media_status === "READY") {
      article.append(makeText("p", "small text-success mt-3 mb-0", `재생 준비 완료 · ${item.media_original_filename || "등록된 음원"}`));
    }
    return article;
  }));
}

function createMediaUploadForm(item) {
  const form = document.createElement("form");
  form.className = "media-upload-form border-top mt-3 pt-3";

  const title = makeText("p", "small fw-bold mb-2", "권한이 확인된 로컬 음원 등록");
  const file = document.createElement("input");
  file.type = "file";
  file.accept = ".mp3,.ogg,.flac,audio/mpeg,audio/ogg,audio/flac";
  file.className = "form-control form-control-sm mb-2";
  file.required = true;

  const note = document.createElement("input");
  note.type = "text";
  note.className = "form-control form-control-sm mb-2";
  note.placeholder = "권리 근거 (예: 직접 제작, 사용 허가 문서 확인)";
  note.maxLength = 500;
  note.required = true;

  const checkWrapper = document.createElement("label");
  checkWrapper.className = "form-check small mb-2";
  const check = document.createElement("input");
  check.type = "checkbox";
  check.className = "form-check-input";
  check.required = true;
  const checkText = document.createElement("span");
  checkText.className = "form-check-label ms-1";
  checkText.textContent = "이 파일의 저장·재생 권한을 확인했습니다.";
  checkWrapper.append(check, checkText);

  const submit = makeText("button", "btn btn-sm btn-primary", "음원 등록");
  submit.type = "submit";
  form.append(title, file, note, checkWrapper, submit);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    submit.disabled = true;
    const body = new FormData();
    body.append("track_id", item.track_id);
    body.append("rights_confirmed", String(check.checked));
    body.append("rights_note", note.value);
    body.append("file", file.files[0]);
    try {
      await request("/api/media/upload", { method: "POST", body });
      await loadReviewList();
    } catch (error) {
      showError(error);
    } finally {
      submit.disabled = false;
    }
  });
  return form;
}

async function loadReviewList() {
  try {
    renderReviewList(await request("/api/requests"));
  } catch (error) {
    showError(error);
  }
}

async function reviewRequest(requestId, decision, rejectReason = null) {
  try {
    await request(`/api/requests/${requestId}/review`, {
      method: "POST",
      body: JSON.stringify({ decision, reject_reason: rejectReason }),
    });
    await loadReviewList();
  } catch (error) {
    showError(error);
  }
}

document.querySelectorAll("[data-action]").forEach((button) => {
  button.addEventListener("click", async () => {
    try {
      button.disabled = true;
      const state = await request("/api/player/control", {
        method: "POST",
        body: JSON.stringify({ action: button.dataset.action }),
      });
      render(state);
    } catch (error) {
      showError(error);
    } finally {
      button.disabled = false;
    }
  });
});

elements.volume.addEventListener("input", () => {
  elements.volumeValue.textContent = `${elements.volume.value}%`;
});

elements.volume.addEventListener("change", async () => {
  try {
    const state = await request("/api/player/volume", {
      method: "PUT",
      body: JSON.stringify({ volume: Number(elements.volume.value) }),
    });
    render(state);
  } catch (error) {
    showError(error);
  }
});

elements.muteButton.addEventListener("click", async () => {
  try {
    const muted = elements.muteButton.getAttribute("aria-pressed") !== "true";
    const state = await request("/api/player/mute", {
      method: "PUT",
      body: JSON.stringify({ muted }),
    });
    render(state);
  } catch (error) {
    showError(error);
  }
});

elements.logoutButton.addEventListener("click", async () => {
  try {
    await request("/api/auth/logout", { method: "POST" });
    window.location.assign("/login");
  } catch (error) {
    showError(error);
  }
});

elements.reviewRefreshButton.addEventListener("click", loadReviewList);

request("/api/player/status").then(render).catch(showError);
loadReviewList();
