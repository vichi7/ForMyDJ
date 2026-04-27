const linkForm = document.querySelector("#linkForm");
const linkInput = document.querySelector("#linkInput");
const formatSelect = document.querySelector("#formatSelect");
const outputDir = document.querySelector("#outputDir");
const chooseOutput = document.querySelector("#chooseOutput");
const outputName = document.querySelector("#outputName");
const outputPath = document.querySelector("#outputPath");
const fileInput = document.querySelector("#fileInput");
const dropZone = document.querySelector("#dropZone");
const jobsEl = document.querySelector("#jobs");
const clearCache = document.querySelector("#clearCache");

async function refreshJobs() {
  const response = await fetch("/api/jobs");
  const data = await response.json();
  if (!outputDir.value) setOutputDir(data.default_output);
  renderJobs(data.jobs);
}

function renderJobs(jobs) {
  if (!jobs.length) {
    jobsEl.innerHTML = `<div class="empty">Paste a link or drop audio files to start.</div>`;
    return;
  }

  jobsEl.innerHTML = jobs.map((job) => {
    const title = escapeHtml(job.title || basename(job.input_value));
    const artist = escapeHtml(job.artist || "Unknown artist");
    const warnings = (job.warnings || []).map(escapeHtml).join(" | ");
    const output = job.output_path ? `<p class="path">${escapeHtml(job.output_path)}</p>` : "";
    const key = job.estimated_key ? `<span>Key: ${escapeHtml(job.estimated_key)}</span>` : "";
    const error = job.error ? `<p class="error">${escapeHtml(job.error)}</p>` : "";
    return `
      <article class="job">
        <div class="job-main">
          <div>
            <h3>${title}</h3>
            <p class="meta"><span>${artist}</span><span>${job.format.toUpperCase()}</span>${key}<span>${escapeHtml(job.progress)}</span></p>
          </div>
          <span class="status ${job.status}">${escapeHtml(job.status)}</span>
        </div>
        ${output}
        ${warnings ? `<p class="warning">${warnings}</p>` : ""}
        ${error}
      </article>
    `;
  }).join("");
}

function basename(value) {
  try {
    return decodeURIComponent(value.split("/").pop()) || value;
  } catch {
    return value;
  }
}

function setOutputDir(path) {
  outputDir.value = path;
  outputName.textContent = folderName(path);
  outputPath.textContent = `in ${parentLabel(path)}`;
  chooseOutput.title = path;
}

function friendlyPath(path) {
  const home = path.startsWith("/Users/") ? path.split("/").slice(0, 3).join("/") : "";
  return path.replace(home, "~").split("/").filter(Boolean).join(" / ") || path;
}

function folderName(path) {
  return path.split("/").filter(Boolean).pop() || path;
}

function parentLabel(path) {
  const parent = path.split("/").filter(Boolean).slice(0, -1).join("/");
  return parent ? friendlyPath(`/${parent}`) : path;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  })[char]);
}

chooseOutput.addEventListener("click", async () => {
  const previousLabel = outputName.textContent;
  chooseOutput.disabled = true;
  outputName.textContent = "Choosing...";
  outputPath.textContent = "";

  try {
    const response = await fetch("/api/output/choose", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ current_path: outputDir.value }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Could not choose output folder");
    if (data.path) {
      setOutputDir(data.path);
    } else {
      outputName.textContent = previousLabel;
      outputPath.textContent = `in ${parentLabel(outputDir.value)}`;
    }
  } catch (error) {
    outputName.textContent = previousLabel;
    outputPath.textContent = `in ${parentLabel(outputDir.value)}`;
    window.alert(error.message);
  } finally {
    chooseOutput.disabled = false;
  }
});

linkForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const link = linkInput.value.trim();
  if (!link) return;
  linkInput.value = "";
  await fetch("/api/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      link,
      format: formatSelect.value,
      output_dir: outputDir.value,
    }),
  });
  refreshJobs();
});

async function uploadFiles(files) {
  for (const file of files) {
    const body = new FormData();
    body.append("file", file);
    body.append("format", formatSelect.value);
    body.append("output_dir", outputDir.value);
    await fetch("/api/upload", { method: "POST", body });
  }
  refreshJobs();
}

fileInput.addEventListener("change", () => uploadFiles(fileInput.files));

dropZone.addEventListener("dragover", (event) => {
  event.preventDefault();
  dropZone.classList.add("dragging");
});

dropZone.addEventListener("dragleave", () => {
  dropZone.classList.remove("dragging");
});

dropZone.addEventListener("drop", (event) => {
  event.preventDefault();
  dropZone.classList.remove("dragging");
  uploadFiles(event.dataTransfer.files);
});

clearCache.addEventListener("click", async () => {
  await fetch("/api/cache/clear", { method: "POST" });
  refreshJobs();
});

refreshJobs();
setInterval(refreshJobs, 1500);
