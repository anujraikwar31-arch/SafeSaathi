const API = window.SAFESAATHI_API || "";
const $ = (id) => document.getElementById(id);

const LABELS = {
  SCAM: "SCAM", SUSPICIOUS: "SUSPICIOUS", SAFE: "LOOKS SAFE",
};

function guessKind(text, file) {
  const value = (text || "").trim();
  if (file) return "image";
  if (/^[\w.\-]{2,64}@[a-zA-Z]{2,32}$/.test(value)) return "upi";
  if (/^(https?:\/\/|www\.)\S+$/i.test(value)) return "link";
  return "text";
}

function escapeHtml(text) {
  return String(text || "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

function signalSummary(result) {
  const parts = [];
  const signals = result.signals || {};
  if (signals.engine) parts.push("engine: " + signals.engine);
  if (signals.classifier !== null && signals.classifier !== undefined) {
    parts.push("classifier: " + Math.round(signals.classifier * 100) + "%");
  }
  if (signals.rules && signals.rules.length) parts.push("flags: " + signals.rules.join(", "));
  (signals.links || []).forEach((link) => {
    const bits = [link.domain];
    if (link.age_days !== null && link.age_days !== undefined) bits.push(link.age_days + " days old");
    if (link.lookalike) bits.push(link.lookalike);
    if (link.safe_browsing) bits.push("flagged by Google Safe Browsing");
    if (link.shortened) bits.push("shortened link");
    parts.push(bits.join(" - "));
  });
  return parts.join("\n");
}

function render(result) {
  const box = $("result");
  const verdict = result.verdict;
  const reasons = (result.reasons || []).map((r) => `<li>${escapeHtml(r)}</li>`).join("");
  const badges = [];
  if (result.seen_count > 1) badges.push(`Checked ${result.seen_count} times`);
  if (result.cached) badges.push("Instant answer from cache");
  badges.push(`${result.latency_ms} ms`);
  if (result.category) badges.push(result.category.replace(/_/g, " "));

  box.innerHTML = `
    <span class="pill ${verdict}">${LABELS[verdict] || verdict}</span>
    <h2>Risk ${result.risk} out of 100</h2>
    <div class="meter ${verdict}"><span style="width:${Math.max(3, result.risk)}%"></span></div>
    <ul class="reasons">${reasons}</ul>
    <div class="advice ${verdict}"><strong>What to do:</strong> ${escapeHtml(result.advice)}</div>
    <div class="badges">${badges.map((b) => `<span class="badge">${escapeHtml(b)}</span>`).join("")}</div>
    ${result.audio_b64 ? `<audio controls src="data:audio/mpeg;base64,${result.audio_b64}"></audio>` : ""}
    <div class="actions">
      <a class="primary" href="https://cybercrime.gov.in" target="_blank" rel="noopener">Report on cybercrime.gov.in</a>
      <a href="tel:1930">Call 1930</a>
      <a href="#" id="wrong">This answer looks wrong</a>
    </div>
    <details><summary>What we checked</summary><pre>${escapeHtml(signalSummary(result))}</pre></details>
    ${result.extracted_text && result.extracted_text.length > 0
      ? `<details><summary>Text we read</summary><pre>${escapeHtml(result.extracted_text)}</pre></details>` : ""}
  `;
  box.hidden = false;
  box.scrollIntoView({ behavior: "smooth", block: "nearest" });

  const wrong = $("wrong");
  if (wrong) {
    wrong.addEventListener("click", async (event) => {
      event.preventDefault();
      await fetch(API + "/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ fingerprint: result.fingerprint, says_scam: verdict === "SAFE", source: "web" }),
      });
      wrong.textContent = "Thank you, we will look at it";
    });
  }
}

async function check() {
  const text = $("content").value.trim();
  const file = $("file").files[0];
  if (!text && !file) {
    $("content").focus();
    return;
  }
  const button = $("check");
  button.disabled = true;
  button.textContent = "Checking...";
  $("result").hidden = false;
  $("result").innerHTML = '<p class="hint">Checking this message. It usually takes 3 to 5 seconds.</p>';

  const form = new FormData();
  form.append("kind", guessKind(text, file));
  form.append("content", text);
  form.append("lang", $("lang").value);
  form.append("source", "web");
  form.append("want_audio", "true");
  if (file) form.append("file", file);

  try {
    const response = await fetch(API + "/api/analyze", { method: "POST", body: form });
    if (!response.ok) throw new Error("Server said " + response.status);
    render(await response.json());
  } catch (error) {
    $("result").innerHTML = `<p class="hint">Could not check that: ${escapeHtml(error.message)}.
      Please try again in a moment.</p>`;
  } finally {
    button.disabled = false;
    button.textContent = "Check";
  }
}

$("check").addEventListener("click", check);
$("clear").addEventListener("click", () => {
  $("content").value = "";
  $("file").value = "";
  $("filename").textContent = "";
  $("result").hidden = true;
});
$("file").addEventListener("change", () => {
  const file = $("file").files[0];
  $("filename").textContent = file ? `Screenshot ready: ${file.name}` : "";
});
document.querySelectorAll(".examples button").forEach((button) => {
  button.addEventListener("click", () => {
    $("content").value = button.dataset.ex;
    $("file").value = "";
    $("filename").textContent = "";
    check();
  });
});
$("content").addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key === "Enter") check();
});
