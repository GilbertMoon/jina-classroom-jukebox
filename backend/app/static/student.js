const csrfToken = document.querySelector('meta[name="csrf-token"]').content;
const form = document.querySelector("#song-request-form");
const list = document.querySelector("#request-list");
const alertBox = document.querySelector("#student-alert");
const submitButton = document.querySelector("#request-button");
const youtubeUrlInput = document.querySelector("#youtube-url");
const titleInput = document.querySelector("#title");
const artistInput = document.querySelector("#artist");
const commentInput = document.querySelector("#comment");

const statusLabels = {
  PENDING: "승인 대기",
  APPROVED: "승인",
  REJECTED: "반려",
};

function showMessage(message, type = "danger") {
  alertBox.textContent = message;
  alertBox.className = `alert alert-${type}`;
}

async function apiRequest(url, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (options.method && options.method !== "GET") {
    headers["X-CSRF-Token"] = csrfToken;
  }
  const response = await fetch(url, { ...options, headers });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.detail || "요청을 처리하지 못했습니다.");
  return payload;
}

function renderRequests(items) {
  if (!items.length) {
    list.innerHTML = '<p class="text-secondary mb-0">아직 신청한 노래가 없습니다.</p>';
    return;
  }
  list.replaceChildren(...items.map((item) => {
    const article = document.createElement("article");
    article.className = "request-item border rounded-3 p-3";

    const heading = document.createElement("h3");
    heading.className = "h6 fw-bold mb-1";
    heading.textContent = item.title;

    const details = document.createElement("p");
    details.className = "small text-secondary mb-2";
    details.textContent = item.artist_or_channel || "가수·채널 미입력";

    const link = document.createElement("a");
    link.href = item.youtube_url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.className = "small";
    link.textContent = "YouTube에서 확인";

    const badge = document.createElement("span");
    badge.className = `badge request-status request-status-${item.status.toLowerCase()}`;
    badge.textContent = statusLabels[item.status] || item.status;

    const top = document.createElement("div");
    top.className = "d-flex justify-content-between gap-3";
    const text = document.createElement("div");
    text.append(heading, details, link);
    top.append(text, badge);
    article.append(top);

    if (item.comment) {
      const comment = document.createElement("p");
      comment.className = "small mt-3 mb-0";
      comment.textContent = `메모: ${item.comment}`;
      article.append(comment);
    }
    if (item.reject_reason) {
      const reason = document.createElement("p");
      reason.className = "small text-danger mt-2 mb-0";
      reason.textContent = `반려 사유: ${item.reject_reason}`;
      article.append(reason);
    }
    return article;
  }));
}

async function loadRequests() {
  try {
    renderRequests(await apiRequest("/api/requests/me"));
  } catch (error) {
    showMessage(error.message);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  alertBox.classList.add("d-none");
  submitButton.disabled = true;
  try {
    await apiRequest("/api/requests", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        youtube_url: youtubeUrlInput.value,
        title: titleInput.value,
        artist_or_channel: artistInput.value || null,
        comment: commentInput.value || null,
      }),
    });
    form.reset();
    showMessage("신청곡이 승인 대기 상태로 등록되었습니다.", "success");
    await loadRequests();
  } catch (error) {
    showMessage(error.message);
  } finally {
    submitButton.disabled = false;
  }
});

document.querySelector("#refresh-button").addEventListener("click", loadRequests);
document.querySelector("#logout-button").addEventListener("click", async () => {
  try {
    await apiRequest("/api/auth/logout", { method: "POST" });
    window.location.assign("/login");
  } catch (error) {
    showMessage(error.message);
  }
});

loadRequests();
