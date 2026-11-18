const csrfToken = document.querySelector('meta[name="csrf-token"]').content;
const form = document.querySelector("#song-request-form");
const list = document.querySelector("#request-list");
const alertBox = document.querySelector("#student-alert");
const submitButton = document.querySelector("#request-button");
const wishButton = document.querySelector("#wish-button");
const wishList = document.querySelector("#wish-list");
const communityList = document.querySelector("#community-list");
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
  const payload = response.status === 204 ? null : await response.json();
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
    if (item.status === "PENDING") {
      const cancel = document.createElement("button");
      cancel.type = "button";
      cancel.className = "btn btn-sm btn-outline-danger mt-3";
      cancel.textContent = "신청 취소";
      cancel.addEventListener("click", async () => {
        if (!window.confirm(`'${item.title}' 신청을 취소할까요?`)) return;
        try {
          await apiRequest(`/api/requests/${item.id}`, { method: "DELETE" });
          showMessage("신청을 취소했습니다.", "success");
          await Promise.all([loadRequests(), loadCommunityRequests()]);
        } catch (error) {
          showMessage(error.message);
        }
      });
      article.append(cancel);
    }
    return article;
  }));
}

function renderWishList(items) {
  if (!items.length) {
    wishList.innerHTML = '<p class="text-secondary mb-0">Wish List가 비어 있습니다.</p>';
    return;
  }
  wishList.replaceChildren(...items.map((item) => {
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
    const controls = document.createElement("div");
    controls.className = "d-flex flex-wrap gap-2 mt-3";
    const requestButton = document.createElement("button");
    requestButton.type = "button";
    requestButton.className = "btn btn-sm btn-primary";
    requestButton.textContent = "신청으로 전환";
    requestButton.addEventListener("click", () => convertWish(item));
    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.className = "btn btn-sm btn-outline-danger";
    deleteButton.textContent = "삭제";
    deleteButton.addEventListener("click", () => deleteWish(item));
    controls.append(requestButton, deleteButton);
    article.append(heading, details, link, controls);
    return article;
  }));
}

function renderCommunityList(items) {
  if (!items.length) {
    communityList.innerHTML = '<p class="text-secondary mb-0">현재 공개할 신청곡이 없습니다.</p>';
    return;
  }
  communityList.replaceChildren(...items.map((item) => {
    const article = document.createElement("article");
    article.className = "request-item border rounded-3 p-3 d-flex flex-wrap justify-content-between align-items-center gap-3";
    const details = document.createElement("div");
    const heading = document.createElement("h3");
    heading.className = "h6 fw-bold mb-1";
    heading.textContent = item.title;
    const summary = document.createElement("p");
    summary.className = "small text-secondary mb-0";
    summary.textContent = `${item.artist_or_channel || "가수·채널 미입력"} · ${statusLabels[item.status]} · ${item.request_count}명 신청`;
    details.append(heading, summary);
    const join = document.createElement("button");
    join.type = "button";
    join.className = "btn btn-sm btn-outline-info";
    join.disabled = item.requested_by_me || item.status !== "PENDING";
    join.textContent = item.requested_by_me
      ? "신청 참여 중"
      : item.status === "PENDING" ? "나도 듣고 싶어요" : "승인 완료";
    join.addEventListener("click", async () => {
      join.disabled = true;
      try {
        await apiRequest(`/api/requests/tracks/${item.track_id}/join`, { method: "POST" });
        showMessage("기존 신청곡에 함께 신청했습니다.", "success");
        await Promise.all([loadCommunityRequests(), loadRequests()]);
      } catch (error) {
        showMessage(error.message);
        join.disabled = false;
      }
    });
    article.append(details, join);
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

async function loadWishList() {
  try {
    renderWishList(await apiRequest("/api/wishlist/me"));
  } catch (error) {
    showMessage(error.message);
  }
}

async function loadCommunityRequests() {
  try {
    renderCommunityList(await apiRequest("/api/requests/community"));
  } catch (error) {
    showMessage(error.message);
  }
}

function formPayload() {
  return {
    youtube_url: youtubeUrlInput.value,
    title: titleInput.value,
    artist_or_channel: artistInput.value || null,
  };
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
        ...formPayload(),
        comment: commentInput.value || null,
      }),
    });
    form.reset();
    showMessage("신청곡이 승인 대기 상태로 등록되었습니다.", "success");
    await loadRequests();
    await loadCommunityRequests();
  } catch (error) {
    showMessage(error.message);
  } finally {
    submitButton.disabled = false;
  }
});

wishButton.addEventListener("click", async () => {
  if (!form.reportValidity()) return;
  alertBox.classList.add("d-none");
  wishButton.disabled = true;
  try {
    await apiRequest("/api/wishlist", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(formPayload()),
    });
    form.reset();
    showMessage("Wish List에 담았습니다.", "success");
    await loadWishList();
  } catch (error) {
    showMessage(error.message);
  } finally {
    wishButton.disabled = false;
  }
});

async function convertWish(item) {
  try {
    await apiRequest(`/api/wishlist/${item.id}/request`, { method: "POST" });
    showMessage("신청곡으로 전환했습니다. Wish List에서는 제거됩니다.", "success");
    await Promise.all([loadWishList(), loadRequests(), loadCommunityRequests()]);
  } catch (error) {
    showMessage(error.message);
  }
}

async function deleteWish(item) {
  if (!window.confirm(`'${item.title}'을 Wish List에서 삭제할까요?`)) return;
  try {
    await apiRequest(`/api/wishlist/${item.id}`, { method: "DELETE" });
    showMessage("Wish List에서 삭제했습니다.", "success");
    await loadWishList();
  } catch (error) {
    showMessage(error.message);
  }
}

document.querySelector("#refresh-button").addEventListener("click", loadRequests);
document.querySelector("#wish-refresh-button").addEventListener("click", loadWishList);
document.querySelector("#community-refresh-button").addEventListener("click", loadCommunityRequests);
document.querySelector("#logout-button").addEventListener("click", async () => {
  try {
    await apiRequest("/api/auth/logout", { method: "POST" });
    window.location.assign("/login");
  } catch (error) {
    showMessage(error.message);
  }
});

loadRequests();
loadWishList();
loadCommunityRequests();
