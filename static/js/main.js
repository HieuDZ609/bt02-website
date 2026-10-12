(function () {
  "use strict";

  var bannerText = document.getElementById("bannerText");
  var bannerClone = document.getElementById("bannerTextClone");
  var bannerTrack = document.getElementById("bannerTrack");
  var form = document.getElementById("messageForm");
  var input = document.getElementById("messageInput");
  var sendBtn = document.getElementById("sendBtn");
  var status = document.getElementById("formStatus");
  var yearEl = document.getElementById("year");

  if (yearEl) {
    yearEl.textContent = new Date().getFullYear();
  }

  function setBanner(message) {
    if (!message || !bannerText) return;
    if (bannerText.textContent === message) return;
    bannerText.textContent = message;
    if (bannerClone) bannerClone.textContent = message;
    if (bannerTrack) {
      var seconds = Math.max(12, Math.min(40, message.length * 0.4));
      bannerTrack.style.animationDuration = seconds + "s";
    }
  }

  function pollBanner() {
    fetch("/api/banner", { headers: { Accept: "application/json" } })
      .then(function (res) { return res.ok ? res.json() : null; })
      .then(function (data) { if (data && data.message) setBanner(data.message); })
      .catch(function () { /* im lặng, thử lại ở lần poll sau */ });
  }

  function showStatus(text, isError) {
    if (!status) return;
    status.textContent = text ? (isError ? "! " : "> ") + text : "";
    status.className = "form-status " + (isError ? "err" : "ok");
  }

  if (form) {
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      var message = (input.value || "").trim();
      if (!message) {
        showStatus("Vui lòng nhập nội dung.", true);
        return;
      }
      sendBtn.disabled = true;
      sendBtn.textContent = "SENDING...";
      showStatus("", false);

      fetch("/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: message })
      })
        .then(function (res) {
          return res.json().then(function (data) {
            return { ok: res.ok, data: data };
          });
        })
        .then(function (result) {
          if (result.ok && result.data.ok) {
            input.value = "";
            showStatus(result.data.message || "Đã gửi thành công!", false);
          } else {
            showStatus((result.data && result.data.error) || "Gửi thất bại.", true);
          }
        })
        .catch(function () {
          showStatus("Không kết nối được máy chủ.", true);
        })
        .finally(function () {
          sendBtn.disabled = false;
          sendBtn.textContent = "SEND";
        });
    });
  }

  pollBanner();
  setInterval(pollBanner, 5000);
})();
