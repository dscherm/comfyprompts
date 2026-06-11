/**
 * comfyui-toolchain · web UI
 * Single-file vanilla JS — no build step, no external deps.
 * All API calls go to the same-origin Flask backend.
 */
(function () {
  "use strict";

  // ── Constants ───────────────────────────────────────────
  const POLL_INTERVAL_STATUS = 10_000;  // ms — status pill refresh
  const POLL_INTERVAL_JOB    =  2_500;  // ms — job progress
  const IMAGE_EXTS = new Set(["png","jpg","jpeg","webp","gif","bmp","tiff"]);

  // ── State ────────────────────────────────────────────────
  let workflows = [];            // [{id, name, description, category, tags, parameters, ...}]
  let selectedWorkflow = null;   // workflow object currently shown
  let activeCategory   = null;   // null = all
  let searchQuery      = "";

  let currentJobId   = null;
  let jobPollTimer   = null;
  let statusPollTimer = null;

  // In-memory session gallery: [{url, filename, type}]
  const galleryItems = [];

  // Authoring state
  let lastValidateOk = false;  // whether last validate call succeeded

  // ── DOM refs ─────────────────────────────────────────────
  const $ = id => document.getElementById(id);

  const dom = {
    // topbar
    tabBtns:      () => document.querySelectorAll(".tab-btn"),
    tabPanels:    () => document.querySelectorAll(".tab-panel"),
    pillDot:      $("pill-dot"),
    pillText:     $("pill-text"),
    pillQueue:    $("pill-queue"),

    // generate — sidebar
    workflowSearch: $("workflow-search"),
    catChips:       $("cat-chips"),
    workflowList:   $("workflow-list"),

    // generate — main
    wfEmpty:      $("wf-empty"),
    wfHeader:     $("wf-header"),
    wfName:       $("wf-name"),
    wfDesc:       $("wf-desc"),
    wfDlNotice:   $("wf-dl-notice"),
    paramForm:    $("param-form"),
    genActions:   $("gen-actions"),
    btnGenerate:  $("btn-generate"),
    progressStrip:$("progress-strip"),
    progressStatus: $("progress-status"),
    progressPct:  $("progress-pct"),
    progressFill: $("progress-fill"),
    genError:     $("gen-error"),
    outputsSection: $("outputs-section"),
    outputCards:  $("output-cards"),
    gallerySection: $("gallery-section"),
    galleryGrid:  $("gallery-grid"),

    // lightbox
    lightbox:     $("lightbox"),
    lightboxImg:  $("lightbox-img"),

    // create tab
    wfSourceSelect: $("wf-source-select"),
    btnLoadSource:  $("btn-load-source"),
    authorId:       $("author-id"),
    wfJsonEditor:   $("wf-json-editor"),
    wfMetaEditor:   $("wf-meta-editor"),
    btnValidate:    $("btn-validate"),
    btnSave:        $("btn-save"),
    validateResults: $("validate-results"),
    validateSummary: $("validate-summary"),
    validateList:    $("validate-list"),
    paramsList:      $("params-list"),
    bridgeTitle:     $("bridge-title"),
    bridgeSpec:      $("bridge-spec"),
    btnQueueRequest: $("btn-queue-request"),
    requestsList:    $("requests-list"),

    // toast
    toastContainer: $("toast-container"),
  };

  // ── Utilities ────────────────────────────────────────────

  /** Show a transient toast message. kind: "error"|"success"|"info" */
  function toast(msg, kind = "error", duration = 4500) {
    const el = document.createElement("div");
    el.className = `toast toast-${kind}`;
    el.textContent = msg;
    dom.toastContainer.appendChild(el);
    setTimeout(() => el.remove(), duration);
  }

  /** Fetch wrapper: returns parsed JSON or throws with a user-friendly message. */
  async function api(path, opts = {}) {
    let resp;
    try {
      resp = await fetch(path, opts);
    } catch (e) {
      throw new Error(`Network error: ${e.message}`);
    }
    let body;
    try {
      body = await resp.json();
    } catch {
      throw new Error(`Server returned non-JSON (HTTP ${resp.status})`);
    }
    if (!resp.ok) {
      const msg = body?.error || body?.detail || `HTTP ${resp.status}`;
      const err = new Error(msg);
      err.status  = resp.status;
      err.body    = body;
      throw err;
    }
    return body;
  }

  /** POST JSON helper */
  function apiPost(path, data) {
    return api(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
  }

  /** Determine if a filename looks like an image */
  function isImage(filename) {
    if (!filename) return false;
    const ext = filename.split(".").pop().toLowerCase();
    return IMAGE_EXTS.has(ext);
  }

  /** Format a 0..1 progress value as "42%" or "…" */
  function fmtPct(p) {
    if (p == null) return "…";
    return `${Math.round(p * 100)}%`;
  }

  /** Kebab → Title Case */
  function titleCase(s) {
    return s.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
  }

  // ── Tab switching ─────────────────────────────────────────
  function switchTab(target) {
    dom.tabBtns().forEach(btn => {
      btn.classList.toggle("active", btn.dataset.tab === target);
    });
    dom.tabPanels().forEach(panel => {
      panel.classList.toggle("active", panel.id === `tab-${target}`);
    });
    // Refresh pending requests on create tab
    if (target === "create") loadPendingRequests();
  }

  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });

  // ── Status polling ────────────────────────────────────────
  async function pollStatus() {
    try {
      const s = await api("/api/status");
      dom.pillDot.className = "pill-dot " + (s.connected ? "connected" : "disconnected");
      dom.pillText.textContent = s.connected ? "connected" : "offline";
      if (s.queue_running != null || s.queue_pending != null) {
        const r = s.queue_running ?? "?";
        const p = s.queue_pending ?? "?";
        dom.pillQueue.textContent = `${r} running · ${p} pending`;
        dom.pillQueue.classList.remove("hidden");
      } else {
        dom.pillQueue.classList.add("hidden");
      }
    } catch {
      dom.pillDot.className = "pill-dot disconnected";
      dom.pillText.textContent = "offline";
    }
  }

  function startStatusPoll() {
    pollStatus();
    statusPollTimer = setInterval(pollStatus, POLL_INTERVAL_STATUS);
  }

  // ── Workflow catalog ──────────────────────────────────────
  async function loadWorkflows() {
    try {
      workflows = await api("/api/workflows");
      renderSidebar();
      populateSourceDropdown();
    } catch (e) {
      toast(`Failed to load workflows: ${e.message}`);
    }
  }

  /** Unique sorted category list from loaded workflows */
  function categories() {
    return [...new Set(workflows.map(w => w.category))].sort();
  }

  /** Render category chips */
  function renderCatChips() {
    dom.catChips.innerHTML = "";
    // "All" chip
    const all = document.createElement("button");
    all.className = "cat-chip" + (activeCategory === null ? " active" : "");
    all.textContent = "All";
    all.addEventListener("click", () => { activeCategory = null; renderSidebar(); });
    dom.catChips.appendChild(all);

    categories().forEach(cat => {
      const btn = document.createElement("button");
      btn.className = "cat-chip" + (activeCategory === cat ? " active" : "");
      btn.textContent = cat;
      btn.addEventListener("click", () => {
        activeCategory = activeCategory === cat ? null : cat;
        renderSidebar();
      });
      dom.catChips.appendChild(btn);
    });
  }

  /** Filter workflows by search + category */
  function filteredWorkflows() {
    const q = searchQuery.toLowerCase();
    return workflows.filter(w => {
      const matchCat = !activeCategory || w.category === activeCategory;
      const matchQ   = !q || w.name.toLowerCase().includes(q) ||
                       (w.description || "").toLowerCase().includes(q) ||
                       (w.tags || []).some(t => t.toLowerCase().includes(q));
      return matchCat && matchQ;
    });
  }

  /** Render sidebar: chips + grouped workflow list */
  function renderSidebar() {
    renderCatChips();
    const list = filteredWorkflows();
    dom.workflowList.innerHTML = "";

    if (!list.length) {
      const empty = document.createElement("div");
      empty.style.cssText = "padding:16px 8px;color:var(--text-3);font-size:12px;";
      empty.textContent = "No workflows match.";
      dom.workflowList.appendChild(empty);
      return;
    }

    // Group by category
    const groups = {};
    list.forEach(w => {
      (groups[w.category] = groups[w.category] || []).push(w);
    });

    Object.keys(groups).sort().forEach(cat => {
      const label = document.createElement("div");
      label.className = "wf-group-label";
      label.textContent = cat;
      dom.workflowList.appendChild(label);

      groups[cat].forEach(w => {
        const item = document.createElement("div");
        item.className = "wf-item" + (selectedWorkflow?.id === w.id ? " active" : "");
        item.dataset.id = w.id;
        item.setAttribute("role", "button");
        item.setAttribute("tabindex", "0");
        item.setAttribute("aria-label", w.name);

        const nameSpan = document.createElement("span");
        nameSpan.className = "wf-item-name";
        nameSpan.textContent = w.name;
        item.appendChild(nameSpan);

        if (w.requires_download) {
          const badge = document.createElement("span");
          badge.className = "wf-dl-badge";
          badge.textContent = "DL";
          const detail = w.requires_download_detail;
          badge.title = detail
            ? (typeof detail === "string" ? detail : JSON.stringify(detail, null, 2))
            : "Requires model download before first use";
          item.appendChild(badge);
        }

        item.addEventListener("click",   () => selectWorkflow(w));
        item.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") selectWorkflow(w); });
        dom.workflowList.appendChild(item);
      });
    });
  }

  // Search handler
  dom.workflowSearch.addEventListener("input", e => {
    searchQuery = e.target.value;
    renderSidebar();
  });

  // ── Workflow selection + form build ───────────────────────
  function selectWorkflow(w) {
    selectedWorkflow = w;
    clearJobState();
    renderSidebar();   // refresh active state
    renderWorkflowForm(w);
  }

  function clearJobState() {
    stopJobPoll();
    currentJobId = null;
    dom.progressStrip.classList.remove("visible");
    dom.genError.classList.remove("visible");
    dom.outputsSection.classList.remove("visible");
  }

  function renderWorkflowForm(w) {
    dom.wfEmpty.classList.add("hidden");
    dom.wfHeader.classList.remove("hidden");
    dom.genActions.classList.remove("hidden");

    dom.wfName.textContent = w.name;
    dom.wfDesc.textContent = w.description || "";

    // Download notice
    if (w.requires_download && w.requires_download_detail) {
      dom.wfDlNotice.classList.add("visible");
      const detail = w.requires_download_detail;
      const detailText = typeof detail === "string"
        ? detail
        : JSON.stringify(detail, null, 2);
      dom.wfDlNotice.innerHTML =
        `<details><summary>Requires download before first use</summary>` +
        `<pre>${escHtml(detailText)}</pre></details>`;
    } else if (w.requires_download) {
      dom.wfDlNotice.classList.add("visible");
      dom.wfDlNotice.textContent = "This workflow requires model downloads before first use.";
    } else {
      dom.wfDlNotice.classList.remove("visible");
    }

    buildForm(w.parameters || []);
  }

  /** Escape HTML for safe insertion */
  function escHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  /**
   * Build a dynamic form from parameter descriptors.
   * Image/mask/_path params get a file-upload widget.
   */
  function buildForm(params) {
    dom.paramForm.innerHTML = "";

    params.forEach(p => {
      const field = document.createElement("div");
      field.className = "form-field";

      // Label
      const label = document.createElement("div");
      label.className = "field-label";
      const labelText = document.createElement("span");
      labelText.textContent = titleCase(p.name);
      label.appendChild(labelText);
      if (p.required) {
        const req = document.createElement("span");
        req.className = "field-required";
        req.textContent = "required";
        label.appendChild(req);
      }
      field.appendChild(label);

      // Description
      if (p.description) {
        const desc = document.createElement("div");
        desc.className = "field-desc";
        desc.textContent = p.description;
        field.appendChild(desc);
      }

      // Determine if this is an image-upload param
      const isImageParam = isImagePathParam(p);

      if (isImageParam) {
        field.appendChild(buildUploadWidget(p));
      } else if (Array.isArray(p.options) && p.options.length) {
        // enum param — render a dropdown
        const sel = document.createElement("select");
        sel.className = "form-input";
        sel.name = p.name;
        sel.id = `param-${p.name}`;
        sel.dataset.paramName = p.name;
        sel.dataset.paramType = p.type || "str";
        p.options.forEach(opt => {
          const o = document.createElement("option");
          o.value = opt;
          o.textContent = opt;
          if (p.default !== undefined && String(opt) === String(p.default)) o.selected = true;
          sel.appendChild(o);
        });
        field.appendChild(sel);
      } else if (p.type === "bool") {
        const wrap = document.createElement("div");
        wrap.className = "checkbox-wrap";
        const cb = document.createElement("input");
        cb.type = "checkbox";
        cb.id = `param-${p.name}`;
        cb.name = p.name;
        cb.dataset.paramName = p.name;
        cb.dataset.paramType = "bool";
        if (p.default !== undefined && p.default !== null) {
          cb.checked = Boolean(p.default);
        }
        const cblabel = document.createElement("label");
        cblabel.htmlFor = `param-${p.name}`;
        cblabel.textContent = p.default !== undefined
          ? `(default: ${p.default})`
          : "(no default)";
        cblabel.style.cssText = "font-size:12px;color:var(--text-3);";
        wrap.appendChild(cb);
        wrap.appendChild(cblabel);
        field.appendChild(wrap);
      } else if (p.type === "int" || p.type === "float") {
        const inp = document.createElement("input");
        inp.type = "number";
        inp.className = "form-input number-input";
        inp.name = p.name;
        inp.id  = `param-${p.name}`;
        inp.dataset.paramName = p.name;
        inp.dataset.paramType = p.type;
        if (p.type === "float") inp.step = "any";
        if (p.default !== undefined && p.default !== null) inp.value = p.default;
        if (p.required) inp.required = true;
        field.appendChild(inp);
      } else {
        // str — textarea if the name contains "prompt", else text input
        const isPrompt = p.name.toLowerCase().includes("prompt");
        const inp = isPrompt
          ? document.createElement("textarea")
          : document.createElement("input");

        if (!isPrompt) inp.type = "text";
        inp.className = "form-input" + (isPrompt ? " textarea" : "");
        inp.name = p.name;
        inp.id   = `param-${p.name}`;
        inp.dataset.paramName = p.name;
        inp.dataset.paramType = "str";
        if (p.default !== undefined && p.default !== null) inp.value = p.default;
        if (p.required) inp.required = true;
        if (!isPrompt) inp.placeholder = p.default !== undefined ? String(p.default) : "";
        field.appendChild(inp);
      }

      dom.paramForm.appendChild(field);
    });
  }

  /** Decide if a parameter should be rendered as an image-upload widget */
  function isImagePathParam(p) {
    const n = p.name.toLowerCase();
    const d = (p.description || "").toLowerCase();
    if (n.includes("image") || n.includes("mask")) return true;
    if ((n.endsWith("_path") || n.endsWith("path")) && d.includes("image")) return true;
    return false;
  }

  /** Build a file-upload widget for image/mask params */
  function buildUploadWidget(p) {
    const zone = document.createElement("label");
    zone.className = "upload-zone";
    zone.htmlFor = `upload-${p.name}`;

    // Hidden file input
    const fileInput = document.createElement("input");
    fileInput.type = "file";
    fileInput.id   = `upload-${p.name}`;
    fileInput.accept = "image/*";
    zone.appendChild(fileInput);

    // Thumbnail (hidden until upload)
    const thumb = document.createElement("img");
    thumb.className = "upload-thumb hidden";
    thumb.alt = "preview";
    zone.appendChild(thumb);

    // Text label
    const labelDiv = document.createElement("div");
    labelDiv.className = "upload-label";
    labelDiv.innerHTML = `<span>Click to upload an image</span>`;
    zone.appendChild(labelDiv);

    // Hidden input storing the server-returned filename
    const serverName = document.createElement("input");
    serverName.type = "hidden";
    serverName.dataset.paramName = p.name;
    serverName.dataset.paramType = "str";
    serverName.dataset.isUpload   = "1";
    zone.appendChild(serverName);

    fileInput.addEventListener("change", async () => {
      const file = fileInput.files[0];
      if (!file) return;

      // Show local preview immediately
      const objUrl = URL.createObjectURL(file);
      thumb.src = objUrl;
      thumb.classList.remove("hidden");
      zone.classList.add("has-file");
      labelDiv.innerHTML = `<span class="upload-filename">${escHtml(file.name)}</span><br><span style="font-size:11px;color:var(--text-3);">Uploading…</span>`;

      // POST to /api/upload
      const form = new FormData();
      form.append("image", file);
      try {
        const result = await api("/api/upload", { method: "POST", body: form });
        serverName.value = result.name;
        labelDiv.innerHTML = `<span class="upload-filename">${escHtml(file.name)}</span>`;
        toast("Image uploaded", "success", 2000);
      } catch (e) {
        zone.classList.remove("has-file");
        thumb.classList.add("hidden");
        serverName.value = "";
        labelDiv.innerHTML = `<span>Click to upload an image</span>`;
        toast(`Upload failed: ${e.message}`);
      }
    });

    return zone;
  }

  // ── Generate form submission ──────────────────────────────

  dom.btnGenerate.addEventListener("click", () => submitGenerate());

  // Enter key on form submits if the generate button is not disabled
  dom.paramForm.addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey && e.target.tagName !== "TEXTAREA") {
      e.preventDefault();
      if (!dom.btnGenerate.disabled) submitGenerate();
    }
  });

  async function submitGenerate() {
    if (!selectedWorkflow) return;

    // Collect param values
    const params = {};
    const missing = [];

    // Named inputs / textareas / selects inside the form
    dom.paramForm.querySelectorAll("[data-param-name]").forEach(el => {
      const name = el.dataset.paramName;
      const type = el.dataset.paramType;

      // Skip upload inputs that haven't been filled
      if (el.dataset.isUpload && !el.value) {
        // Check if this param is required
        const def = selectedWorkflow.parameters.find(p => p.name === name);
        if (def?.required) missing.push(name);
        return;
      }

      let val;
      if (type === "bool") {
        val = el.checked;
      } else if (type === "int") {
        val = el.value !== "" ? parseInt(el.value, 10) : undefined;
      } else if (type === "float") {
        val = el.value !== "" ? parseFloat(el.value) : undefined;
      } else {
        val = el.value;
      }

      if (val !== undefined && val !== "") {
        params[name] = val;
      } else {
        const def = selectedWorkflow.parameters.find(p => p.name === name);
        if (def?.required) missing.push(name);
      }
    });

    if (missing.length) {
      dom.genError.textContent = `Required fields missing: ${missing.join(", ")}`;
      dom.genError.classList.add("visible");
      return;
    }

    dom.genError.classList.remove("visible");
    dom.outputsSection.classList.remove("visible");
    dom.btnGenerate.disabled = true;

    try {
      const result = await apiPost("/api/generate", {
        workflow_id: selectedWorkflow.id,
        params,
      });
      currentJobId = result.prompt_id;
      startJobPoll(currentJobId);
    } catch (e) {
      showGenError(e.message || "Unknown error from /api/generate");
      dom.btnGenerate.disabled = false;
    }
  }

  function showGenError(msg) {
    dom.genError.textContent = msg;
    dom.genError.classList.add("visible");
    dom.progressStrip.classList.remove("visible");
  }

  // ── Job polling ───────────────────────────────────────────
  function startJobPoll(id) {
    setProgress("pending", null);
    dom.progressStrip.classList.add("visible");
    stopJobPoll();
    jobPollTimer = setInterval(() => pollJob(id), POLL_INTERVAL_JOB);
    pollJob(id);  // immediate first check
  }

  function stopJobPoll() {
    if (jobPollTimer) { clearInterval(jobPollTimer); jobPollTimer = null; }
  }

  async function pollJob(id) {
    let job;
    try {
      job = await api(`/api/job/${id}`);
    } catch (e) {
      // Network glitch — don't kill the poll
      toast(`Job poll error: ${e.message}`, "error", 3000);
      return;
    }

    setProgress(job.status, job.progress);

    if (job.status === "completed") {
      stopJobPoll();
      dom.btnGenerate.disabled = false;
      renderOutputs(job.outputs || []);
    } else if (job.status === "error") {
      stopJobPoll();
      dom.btnGenerate.disabled = false;
      dom.progressStrip.classList.remove("visible");
      showGenError(job.error || "Generation failed (unknown error)");
    }
  }

  /** Update the inline progress strip */
  function setProgress(status, progress) {
    const labels = {
      pending:   "Queued…",
      running:   "Generating…",
      completed: "Complete",
      error:     "Error",
    };
    dom.progressStatus.textContent = labels[status] || status;
    dom.progressPct.textContent    = fmtPct(progress);

    if (progress != null) {
      dom.progressFill.classList.remove("indeterminate");
      dom.progressFill.style.width = `${Math.round(progress * 100)}%`;
    } else {
      dom.progressFill.classList.add("indeterminate");
      dom.progressFill.style.width = "40%";
    }
  }

  // ── Render outputs ────────────────────────────────────────
  function renderOutputs(outputs) {
    dom.progressStrip.classList.remove("visible");
    dom.outputsSection.classList.add("visible");
    dom.outputCards.innerHTML = "";

    outputs.forEach(out => {
      if (!out.filename) return;

      if (isImage(out.filename)) {
        // Image card
        const card = document.createElement("div");
        card.className = "output-card";
        const img = document.createElement("img");
        img.src = out.url;
        img.alt = out.filename;
        img.loading = "lazy";
        img.title   = out.filename;
        card.appendChild(img);
        card.addEventListener("click", () => openLightbox(out.url));
        dom.outputCards.appendChild(card);

        // Add to session gallery
        addToGallery({ url: out.url, filename: out.filename });
      } else {
        // Non-image download link
        const card = document.createElement("div");
        card.className = "output-card";
        const link = document.createElement("a");
        link.className = "output-card-link";
        link.href = out.url;
        link.download = out.filename;
        link.textContent = out.filename;
        link.title = "Download";
        card.appendChild(link);
        dom.outputCards.appendChild(card);
      }
    });
  }

  // ── Session gallery ───────────────────────────────────────
  function addToGallery(item) {
    galleryItems.unshift(item);  // newest at index 0
    renderGallery();
    dom.gallerySection.classList.remove("hidden");
  }

  function renderGallery() {
    dom.galleryGrid.innerHTML = "";
    // galleryItems is newest-first; forEach + appendChild preserves that order
    galleryItems.forEach(item => {
      const img = document.createElement("img");
      img.className = "gallery-thumb";
      img.src = item.url;
      img.alt = item.filename;
      img.loading = "lazy";
      img.title = item.filename;
      img.addEventListener("click", () => openLightbox(item.url));
      dom.galleryGrid.appendChild(img);
    });
  }

  // ── Lightbox ──────────────────────────────────────────────
  function openLightbox(url) {
    dom.lightboxImg.src = url;
    dom.lightbox.classList.add("open");
  }

  dom.lightbox.addEventListener("click", () => {
    dom.lightbox.classList.remove("open");
    dom.lightboxImg.src = "";
  });

  document.addEventListener("keydown", e => {
    if (e.key === "Escape" && dom.lightbox.classList.contains("open")) {
      dom.lightbox.classList.remove("open");
      dom.lightboxImg.src = "";
    }
  });

  // ── Create tab ────────────────────────────────────────────

  /** Populate the "Start from" dropdown with loaded workflows */
  function populateSourceDropdown() {
    // Keep "blank" option then append workflows
    const sel = dom.wfSourceSelect;
    // Remove dynamic options (keep first "-- blank --" option)
    while (sel.options.length > 1) sel.remove(1);

    workflows.forEach(w => {
      const opt = document.createElement("option");
      opt.value = w.id;
      opt.textContent = `${w.name} (${w.category})`;
      sel.appendChild(opt);
    });
  }

  dom.btnLoadSource.addEventListener("click", async () => {
    const id = dom.wfSourceSelect.value;
    if (!id) {
      // "blank" — reset editors
      dom.wfJsonEditor.value = "{}";
      dom.wfMetaEditor.value = JSON.stringify({
        name: "",
        description: "",
        category: "other",
        tags: [],
      }, null, 2);
      dom.authorId.value = "";
      resetValidate();
      return;
    }

    try {
      const data = await api(`/api/author/workflow/${id}`);
      dom.wfJsonEditor.value = JSON.stringify(data.workflow, null, 2);
      dom.wfMetaEditor.value = JSON.stringify(data.meta, null, 2);
      dom.authorId.value = data.id;
      resetValidate();
      toast("Workflow loaded", "success", 2000);
    } catch (e) {
      toast(`Load failed: ${e.message}`);
    }
  });

  // Any edit in either editor resets validate state
  [dom.wfJsonEditor, dom.wfMetaEditor].forEach(ed => {
    ed.addEventListener("input", resetValidate);
  });

  function resetValidate() {
    lastValidateOk = false;
    dom.btnSave.disabled = true;
    dom.validateResults.classList.remove("visible");
    dom.wfJsonEditor.classList.remove("error", "ok");
    dom.wfMetaEditor.classList.remove("error", "ok");
  }

  dom.btnValidate.addEventListener("click", async () => {
    let workflow, meta;
    try {
      workflow = JSON.parse(dom.wfJsonEditor.value);
    } catch (e) {
      dom.wfJsonEditor.classList.add("error");
      toast(`Workflow JSON parse error: ${e.message}`);
      return;
    }
    try {
      meta = dom.wfMetaEditor.value.trim() ? JSON.parse(dom.wfMetaEditor.value) : null;
    } catch (e) {
      dom.wfMetaEditor.classList.add("error");
      toast(`Meta JSON parse error: ${e.message}`);
      return;
    }

    dom.btnValidate.disabled = true;
    try {
      const result = await apiPost("/api/author/validate", { workflow, meta });
      renderValidateResults(result);
      lastValidateOk = result.ok;
      dom.btnSave.disabled = !result.ok;
      dom.wfJsonEditor.classList.toggle("ok",    result.ok);
      dom.wfJsonEditor.classList.toggle("error", !result.ok);
    } catch (e) {
      toast(`Validate request failed: ${e.message}`);
    } finally {
      dom.btnValidate.disabled = false;
    }
  });

  function renderValidateResults(r) {
    dom.validateResults.classList.add("visible");

    dom.validateSummary.className = "validate-summary " + (r.ok ? "ok" : r.errors?.length ? "fail" : "warn");
    dom.validateSummary.textContent = r.ok
      ? "Validation passed" + (r.warnings?.length ? ` (${r.warnings.length} warning${r.warnings.length > 1 ? "s" : ""})` : "")
      : `Validation failed — ${r.errors?.length ?? 0} error(s)`;

    const list = dom.validateList;
    list.innerHTML = "";

    (r.errors || []).forEach(msg => {
      const li = document.createElement("li");
      li.innerHTML = `<i class="vl-icon vl-err">[E]</i><span class="vl-err">${escHtml(msg)}</span>`;
      list.appendChild(li);
    });
    (r.warnings || []).forEach(msg => {
      const li = document.createElement("li");
      li.innerHTML = `<i class="vl-icon vl-warn">[W]</i><span class="vl-warn">${escHtml(msg)}</span>`;
      list.appendChild(li);
    });
    if (r.ok && !r.errors?.length && !r.warnings?.length) {
      const li = document.createElement("li");
      li.innerHTML = `<i class="vl-icon vl-ok">[ok]</i><span class="vl-ok">No issues found</span>`;
      list.appendChild(li);
    }

    // Params found
    if (r.params_found?.length) {
      dom.paramsList.innerHTML = "Params found: " +
        r.params_found.map(p => `<code>${escHtml(p)}</code>`).join(" ");
      dom.paramsList.classList.remove("hidden");
    } else {
      dom.paramsList.classList.add("hidden");
    }
  }

  dom.btnSave.addEventListener("click", async () => {
    const id = dom.authorId.value.trim();
    if (!id) { toast("Enter a workflow ID (snake_case)"); return; }

    let workflow, meta;
    try { workflow = JSON.parse(dom.wfJsonEditor.value); } catch (e) { toast(`Workflow JSON: ${e.message}`); return; }
    try { meta = dom.wfMetaEditor.value.trim() ? JSON.parse(dom.wfMetaEditor.value) : {}; } catch (e) { toast(`Meta JSON: ${e.message}`); return; }

    dom.btnSave.disabled = true;
    try {
      const result = await apiPost("/api/author/save", { id, workflow, meta });
      toast(`Saved: ${result.saved}`, "success");
      await loadWorkflows(); // refresh catalog
    } catch (e) {
      if (e.status === 409) {
        // Offer overwrite confirm
        const ok = window.confirm(`"${id}" already exists. Overwrite?`);
        if (ok) {
          try {
            const result = await apiPost("/api/author/save", { id, workflow, meta, overwrite: true });
            toast(`Overwritten: ${result.saved}`, "success");
            await loadWorkflows();
          } catch (e2) {
            toast(`Save failed: ${e2.message}`);
          }
        }
      } else {
        toast(`Save failed: ${e.message}`);
      }
      dom.btnSave.disabled = false;
    }
  });

  // ── Bridge / request queue ────────────────────────────────
  dom.btnQueueRequest.addEventListener("click", async () => {
    const title = dom.bridgeTitle.value.trim();
    const spec  = dom.bridgeSpec.value.trim();
    if (!title || !spec) { toast("Title and spec are both required"); return; }

    dom.btnQueueRequest.disabled = true;
    try {
      const result = await apiPost("/api/author/request", { title, spec });
      toast(`Queued: ${result.queued}`, "success");
      dom.bridgeTitle.value = "";
      dom.bridgeSpec.value  = "";
      await loadPendingRequests();
    } catch (e) {
      toast(`Queue failed: ${e.message}`);
    } finally {
      dom.btnQueueRequest.disabled = false;
    }
  });

  async function loadPendingRequests() {
    try {
      const items = await api("/api/author/requests");
      renderPendingRequests(items);
    } catch {
      // Non-fatal — just leave the list as-is
    }
  }

  function renderPendingRequests(items) {
    dom.requestsList.innerHTML = "";
    if (!items.length) {
      const empty = document.createElement("div");
      empty.style.cssText = "font-size:12px;color:var(--text-3);padding:4px 0;";
      empty.textContent = "No pending requests.";
      dom.requestsList.appendChild(empty);
      return;
    }

    items.forEach(item => {
      const row = document.createElement("div");
      row.className = "request-item";
      const title = document.createElement("span");
      title.className = "request-item-title";
      title.textContent = item.title || "(untitled)";
      const file = document.createElement("span");
      file.className = "request-item-file";
      file.textContent = item.file;
      row.appendChild(title);
      row.appendChild(file);
      dom.requestsList.appendChild(row);
    });
  }

  // ── Initial load ──────────────────────────────────────────
  function init() {
    // Show empty state initially
    dom.wfHeader.classList.add("hidden");
    dom.genActions.classList.add("hidden");
    dom.gallerySection.classList.add("hidden");

    // Default: save disabled until validate passes
    dom.btnSave.disabled = true;

    // Set blank editors
    dom.wfJsonEditor.value = "{}";
    dom.wfMetaEditor.value = JSON.stringify({
      name: "",
      description: "",
      category: "other",
      tags: [],
    }, null, 2);

    startStatusPoll();
    loadWorkflows();
  }

  init();

})();
