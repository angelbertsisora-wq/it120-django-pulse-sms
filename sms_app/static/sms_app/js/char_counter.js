(function () {
  const textarea = document.getElementById("id_message");
  const countEl = document.getElementById("char-count");
  const hintEl = document.getElementById("char-hint");
  const meter = document.querySelector(".char-meter");

  if (!textarea || !countEl) {
    return;
  }

  const SEGMENT = 160;

  function update() {
    const len = textarea.value.length;
    countEl.textContent = String(len);

    if (meter) {
      meter.classList.toggle("over", len > SEGMENT);
    }

    if (hintEl) {
      if (len === 0) {
        hintEl.textContent = "~1 SMS segment (GSM-7)";
      } else {
        const segments = Math.ceil(len / SEGMENT);
        hintEl.textContent =
          segments === 1
            ? "~1 SMS segment (GSM-7)"
            : `~${segments} SMS segments (approx.)`;
      }
    }
  }

  textarea.addEventListener("input", update);
  update();
})();
