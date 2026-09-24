const API = window.SAFESAATHI_API || "";

function escapeHtml(text) {
  return String(text || "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

function tile(big, label) {
  return `<div class="tile"><div class="big">${big}</div><div class="label">${label}</div></div>`;
}

function sparkline(daily) {
  const values = daily.map((d) => d.checks);
  const max = Math.max(1, ...values);
  const width = 520;
  const height = 120;
  const step = values.length > 1 ? width / (values.length - 1) : width;
  const points = values.map((v, i) => `${i * step},${height - (v / max) * (height - 16) - 8}`).join(" ");
  const labels = daily.map((d, i) =>
    `<text x="${i * step}" y="${height + 16}" font-size="11" fill="#8b8f97" text-anchor="middle">${d.date.slice(5)}</text>`
  ).join("");
  const dots = values.map((v, i) =>
    `<circle cx="${i * step}" cy="${height - (v / max) * (height - 16) - 8}" r="3.5" fill="#d63a2f"/>`
  ).join("");
  return `<svg viewBox="-10 -10 ${width + 20} ${height + 36}" width="100%" height="170" role="img" aria-label="checks per day">
      <polyline fill="none" stroke="#16181d" stroke-width="2" points="${points}"/>
      ${dots}${labels}
    </svg>`;
}

async function load() {
  let data;
  try {
    const response = await fetch(API + "/api/stats");
    data = await response.json();
  } catch (error) {
    document.getElementById("tiles").innerHTML = '<p class="hint">Could not reach the API.</p>';
    return;
  }

  document.getElementById("tiles").innerHTML = [
    tile(data.total_checks, "messages checked"),
    tile(data.by_verdict.SCAM || 0, "scams caught"),
    tile(data.scam_share + "%", "flagged as scam or suspicious"),
    tile(data.languages_used || 0, "languages used"),
  ].join("");

  const maxCategory = Math.max(1, ...data.by_category.map((c) => c.count));
  document.getElementById("categories").innerHTML = data.by_category.length
    ? data.by_category.map((c) => `
        <div class="bar-row">
          <span>${escapeHtml(c.category.replace(/_/g, " "))}</span>
          <span class="track"><span style="width:${(c.count / maxCategory) * 100}%"></span></span>
          <span>${c.count}</span>
        </div>`).join("")
    : '<p class="hint">No scams checked yet.</p>';

  document.getElementById("daily").innerHTML = sparkline(data.daily || []);

  const body = document.querySelector("#trending tbody");
  body.innerHTML = data.trending.length
    ? data.trending.map((t) => `
        <tr><td>${escapeHtml(t.snippet || "")}</td>
        <td>${escapeHtml((t.category || "").replace(/_/g, " "))}</td>
        <td>${t.count}</td></tr>`).join("")
    : '<tr><td colspan="3" class="hint">Nothing trending yet.</td></tr>';
}

load();
setInterval(load, 30000);
