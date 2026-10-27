const stateLabels = {
  stopped: ["정지", "text-bg-secondary"],
  playing: ["재생 중", "text-bg-success"],
  paused: ["일시정지", "text-bg-warning"],
};

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
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
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

request("/api/player/status").then(render).catch(showError);
