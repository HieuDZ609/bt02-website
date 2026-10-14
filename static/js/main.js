(function () {
  "use strict";

  var bannerViewport = document.querySelector(".banner__viewport");
  var bannerTrack = document.getElementById("bannerTrack");
  var bannerText = document.getElementById("bannerText");
  var form = document.getElementById("messageForm");
  var input = document.getElementById("messageInput");
  var sendBtn = document.getElementById("sendBtn");
  var status = document.getElementById("formStatus");
  var yearEl = document.getElementById("year");

  var BANNER_SPEED = 60; // px/giây
  var reduceMotion =
    window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  if (yearEl) {
    yearEl.textContent = new Date().getFullYear();
  }

  function clearToBase() {
    var items = bannerTrack.querySelectorAll(".banner__item");
    for (var i = items.length - 1; i >= 1; i--) {
      items[i].remove();
    }
  }

  function startLoop() {
    bannerTrack.classList.remove("is-entering");
    bannerTrack.style.transition = "none";
    bannerTrack.style.transform = "";
    void bannerTrack.offsetWidth;
    bannerTrack.style.transition = "";
    bannerTrack.classList.add("is-looping");
  }

  function startEnter() {
    bannerTrack.classList.remove("is-looping", "is-entering");
    bannerTrack.style.transition = "none";
    bannerTrack.style.transform = "translateX(var(--enter))";
    void bannerTrack.offsetWidth; // chốt vị trí xuất phát ở mép phải
    bannerTrack.style.transition = "";
    bannerTrack.classList.add("is-entering");
    void bannerTrack.offsetWidth;
    bannerTrack.style.transform = "translateX(0)";

    var done = false;
    function finish() {
      if (done) return;
      done = true;
      bannerTrack.removeEventListener("transitionend", finish);
      startLoop();
    }
    bannerTrack.addEventListener("transitionend", finish);
    var secs = parseFloat(
      bannerTrack.style.getPropertyValue("--enter-duration")
    );
    setTimeout(finish, (isFinite(secs) ? secs : 6) * 1000 + 120);
  }

  function buildBanner(message, withEntry) {
    if (!bannerViewport || !bannerTrack || !bannerText) return;
    clearToBase();
    bannerText.textContent = message;

    var vpW = bannerViewport.clientWidth;
    var itemW = bannerText.getBoundingClientRect().width;
    if (!vpW || !itemW) return;

    // đủ bản sao để dải luôn phủ kín thanh: (copies - 1) * itemW >= vpW
    var copies = Math.max(2, Math.ceil(vpW / itemW) + 1);
    for (var i = 1; i < copies; i++) {
      var clone = bannerText.cloneNode(true);
      clone.removeAttribute("id");
      clone.setAttribute("aria-hidden", "true");
      bannerTrack.appendChild(clone);
    }

    bannerTrack.style.setProperty("--shift", itemW + "px");
    bannerTrack.style.setProperty("--enter", vpW + "px");
    bannerTrack.style.setProperty("--loop-duration", itemW / BANNER_SPEED + "s");
    bannerTrack.style.setProperty(
      "--enter-duration",
      vpW / BANNER_SPEED + "s"
    );

    if (reduceMotion) return;
    if (withEntry) startEnter();
    else startLoop();
  }

  function setBanner(message) {
    if (!message || !bannerText) return;
    if (bannerText.textContent === message) return;
    buildBanner(message, true);
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

  if (bannerTrack && bannerText) {
    var started = false;
    function buildInitial() {
      if (started) return;
      started = true;
      buildBanner(bannerText.textContent, true);
    }
    // hoãn build đầu tiên tới khi font tải xong để đo đúng bề rộng;
    // fallback timeout phòng khi font treo
    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(buildInitial);
      setTimeout(buildInitial, 1500);
    } else {
      buildInitial();
    }
    var resizeTimer = null;
    window.addEventListener("resize", function () {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(function () {
        if (!started) return;
        buildBanner(bannerText.textContent, false);
      }, 200);
    });
  }

  pollBanner();
  setInterval(pollBanner, 5000);
})();
