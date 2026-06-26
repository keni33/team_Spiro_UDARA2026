/**
 * StructGuard AI — Page Controllers
 * ====================================
 * Teaching note: Each section below handles one "page" (screen).
 * The pages.load() function is called by the router when navigating.
 * Each page fetches its own data from the API and renders it.
 */

/* ================================================================== */
/* PAGE LOADER — dispatches to the right loader function               */
/* ================================================================== */
const pages = {
  load(page) {
    const loaders = {
      dashboard:  () => dashboardPage.load(),
      projects:   () => projectsPage.load(),
      submit:     () => submitPage.load(),
      inspect:    () => inspectPage.load(),
      analytics:  () => analyticsPage.load(),
      users:      () => usersPage.load(),
      profile:    () => profilePage.load(),
    };
    loaders[page]?.();
  }
};

/* ================================================================== */
/* DASHBOARD PAGE                                                       */
/* ================================================================== */
const dashboardPage = {
  async load() {
    const user = auth.getUser();
    if (!user) return;

    // Fetch stats
    const [statsRes, projectsRes] = await Promise.all([
      api.get("/projects/stats"),
      api.get("/projects?per_page=5"),
    ]);

    const stats    = statsRes.data.stats    || {};
    const projects = projectsRes.data.projects || [];

    // Agency admin / inspector get an extra call for priority queue
    let priority = [];
    if (roles.canSeeAll(user)) {
      const adminRes = await api.get("/admin/dashboard");
      priority = adminRes.data.priority_queue || [];
    }

    this.render(user, stats, projects, priority);
  },

  render(user, stats, projects, priority) {
    const el = document.getElementById("dashboard-content");
    if (!el) return;

    // Build stat cards based on role
    const statCards = roles.canSeeAll(user) ? `
      <div class="stat-card">
        <div class="stat-icon">🏗️</div>
        <div class="stat-label">Total Projects</div>
        <div class="stat-value">${stats.total || 0}</div>
        <div class="stat-meta">registered on platform</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">🚨</div>
        <div class="stat-label">Flagged Sites</div>
        <div class="stat-value" style="color:var(--risk-high)">${stats.flagged || 0}</div>
        <div class="stat-meta">need inspection</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">🔴</div>
        <div class="stat-label">Critical Risk</div>
        <div class="stat-value" style="color:var(--risk-critical)">${stats.critical || 0}</div>
        <div class="stat-meta">highest priority</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">🛑</div>
        <div class="stat-label">Stop-Work Orders</div>
        <div class="stat-value" style="color:var(--risk-critical)">${stats.stop_work || 0}</div>
        <div class="stat-meta">active orders</div>
      </div>
    ` : `
      <div class="stat-card">
        <div class="stat-icon">🏗️</div>
        <div class="stat-label">My Projects</div>
        <div class="stat-value">${stats.total || 0}</div>
        <div class="stat-meta">registered sites</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">✅</div>
        <div class="stat-label">Active</div>
        <div class="stat-value" style="color:var(--risk-safe)">${stats.active || 0}</div>
        <div class="stat-meta">under construction</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">⚠️</div>
        <div class="stat-label">Flagged</div>
        <div class="stat-value" style="color:var(--risk-high)">${stats.flagged || 0}</div>
        <div class="stat-meta">need attention</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">🏁</div>
        <div class="stat-label">Completed</div>
        <div class="stat-value">${stats.completed || 0}</div>
        <div class="stat-meta">finished projects</div>
      </div>
    `;

    const recentRows = projects.length ? projects.map(p => `
      <tr>
        <td><span style="font-family:monospace;font-size:12px;color:var(--brand-primary)">${p.sgid}</span></td>
        <td><strong>${p.name}</strong><br><small style="color:var(--text-muted)">${p.address}</small></td>
        <td>${risk.badge(p.risk_level)}</td>
        <td>${utils.statusBadge(p.status)}</td>
        <td>${utils.formatDate(p.updated_at)}</td>
        <td><button class="btn btn-sm btn-ghost" onclick="projectsPage.viewProject(${p.id})">View →</button></td>
      </tr>
    `).join("") : `<tr><td colspan="6"><div class="empty-state" style="padding:30px"><div class="empty-icon">🏗️</div><div class="empty-title">No projects yet</div><div class="empty-desc">Register your first construction site to get started</div></div></td></tr>`;

    const prioritySection = roles.canSeeAll(user) && priority.length ? `
      <div class="card" style="margin-top:20px">
        <div class="card-header">
          <span class="card-title">🔴 Priority Inspection Queue</span>
          <button class="btn btn-sm btn-ghost" onclick="router.navigate('inspect')">View all →</button>
        </div>
        <div class="card-body">
          ${priority.slice(0, 5).map((p, i) => `
            <div class="priority-item">
              <div class="priority-rank">#${i + 1}</div>
              <div class="priority-info">
                <div class="priority-name">${p.name}</div>
                <div class="priority-addr">${p.address} · ${p.sgid}</div>
              </div>
              ${risk.badge(p.risk_level)}
              <div class="priority-score" style="color:${risk.colour(p.risk_level)}">${Math.round(p.risk_score || 0)}</div>
              <button class="btn btn-sm btn-secondary" onclick="projectsPage.viewProject(${p.id})">Inspect</button>
            </div>
          `).join("")}
        </div>
      </div>
    ` : "";

    el.innerHTML = `
      <div class="section-header">
        <div>
          <div class="section-title">Welcome back, ${user.name.split(" ")[0]} 👋</div>
          <div class="section-sub">${roles.label(user.role)} · ${utils.formatDate(new Date().toISOString())}</div>
        </div>
        ${roles.canSubmit(user) ? `<button class="btn btn-primary" onclick="router.navigate('submit')">📸 New Submission</button>` : ""}
      </div>

      <div class="stat-grid">${statCards}</div>

      <div class="card" style="margin-top:24px">
        <div class="card-header">
          <span class="card-title">Recent Projects</span>
          <button class="btn btn-sm btn-ghost" onclick="router.navigate('projects')">View all →</button>
        </div>
        <div class="table-wrap">
          <table>
            <thead><tr>
              <th>SGID</th><th>Project</th><th>Risk</th><th>Status</th><th>Updated</th><th></th>
            </tr></thead>
            <tbody>${recentRows}</tbody>
          </table>
        </div>
      </div>
      ${prioritySection}
    `;
  }
};

/* ================================================================== */
/* PROJECTS PAGE                                                        */
/* ================================================================== */
const projectsPage = {
  projects: [],
  currentProject: null,

  async load() {
    const el = document.getElementById("projects-content");
    if (!el) return;

    el.innerHTML = `<div class="loading-state"><div class="spinner spinner-lg"></div><p>Loading projects...</p></div>`;

    const res = await api.get("/projects?per_page=50");
    if (!res.ok) { el.innerHTML = `<div class="alert alert-error"><span>❌</span>${res.data.error}</div>`; return; }

    this.projects = res.data.projects || [];
    this.render(el);
  },

  render(el) {
    const user = auth.getUser();
    const rows = this.projects.length ? this.projects.map(p => `
      <tr>
        <td><span style="font-family:monospace;font-size:12px;color:var(--brand-primary);font-weight:600">${p.sgid}</span></td>
        <td>
          <div style="font-weight:600">${p.name}</div>
          <div style="font-size:12px;color:var(--text-muted)">${p.address}</div>
        </td>
        <td>${p.building_type ? p.building_type.charAt(0).toUpperCase() + p.building_type.slice(1) : '—'}</td>
        <td>${p.floors || 1} floor${(p.floors || 1) !== 1 ? 's' : ''}</td>
        <td>${risk.badge(p.risk_level)}</td>
        <td>${utils.statusBadge(p.status)}</td>
        <td>${p.submission_count || 0}</td>
        <td>
          <button class="btn btn-sm btn-secondary" onclick="projectsPage.viewProject(${p.id})">View</button>
          ${user && roles.canEnforce(user) && p.status !== "stop_work" ? `<button class="btn btn-sm btn-danger" style="margin-left:6px" onclick="projectsPage.stopWork(${p.id})">Stop Work</button>` : ""}
        </td>
      </tr>
    `).join("") : `<tr><td colspan="8"><div class="empty-state" style="padding:40px">
      <div class="empty-icon">🏗️</div>
      <div class="empty-title">No projects found</div>
      <div class="empty-desc">Register your first construction site to begin monitoring</div>
      ${roles.canSubmit(auth.getUser()) ? `<button class="btn btn-primary" style="margin-top:16px" onclick="projectsPage.showRegisterModal()">Register a Project</button>` : ""}
    </div></td></tr>`;

    el.innerHTML = `
      <div class="section-header">
        <div>
          <div class="section-title">Construction Projects</div>
          <div class="section-sub">${this.projects.length} project${this.projects.length !== 1 ? 's' : ''} found</div>
        </div>
        ${roles.canSubmit(auth.getUser()) ? `<button class="btn btn-primary" onclick="projectsPage.showRegisterModal()">+ Register Project</button>` : ""}
      </div>
      <div class="card">
        <div class="table-wrap">
          <table>
            <thead><tr>
              <th>SGID</th><th>Project Name</th><th>Type</th><th>Floors</th><th>Risk</th><th>Status</th><th>Submissions</th><th>Actions</th>
            </tr></thead>
            <tbody>${rows}</tbody>
          </table>
        </div>
      </div>
    `;
  },

  async viewProject(id) {
    const res = await api.get(`/projects/${id}`);
    if (!res.ok) { toast.error(res.data.error); return; }
    this.currentProject = res.data.project;
    this.renderProjectModal(this.currentProject);
  },

  renderProjectModal(p) {
    const user = auth.getUser();
    const subs = (p.submissions || []);

    modal.show(`
      <div class="modal-header">
        <div>
          <div class="modal-title">${p.name}</div>
          <div style="font-size:12px;color:var(--text-muted)">${p.sgid} · ${p.address}</div>
        </div>
        <button class="btn-close" onclick="modal.close()">✕</button>
      </div>
      <div class="modal-body">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:20px">
          <div><strong>Building Type</strong><br><span style="color:var(--text-secondary)">${(p.building_type||'').charAt(0).toUpperCase()+(p.building_type||'').slice(1)}</span></div>
          <div><strong>Floors</strong><br><span style="color:var(--text-secondary)">${p.floors || 1}</span></div>
          <div><strong>Permit Ref</strong><br><span style="color:var(--text-secondary)">${p.permit_ref || 'Not provided'}</span></div>
          <div><strong>Started</strong><br><span style="color:var(--text-secondary)">${utils.formatDate(p.start_date)}</span></div>
        </div>

        <div style="display:flex;gap:12px;margin-bottom:20px">
          ${risk.badge(p.risk_level)}
          ${utils.statusBadge(p.status)}
          <span style="font-size:13px;color:var(--text-muted)">Score: ${Math.round(p.risk_score || 0)}/100</span>
        </div>

        <div class="risk-bar-wrap" style="margin-bottom:20px">
          <div class="risk-bar-track"><div class="risk-bar-fill ${risk.fillClass(p.risk_level)}" style="width:${p.risk_score || 0}%"></div></div>
          <div class="risk-bar-label">${Math.round(p.risk_score || 0)}%</div>
        </div>

        <strong>Recent Submissions (${subs.length})</strong>
        ${subs.length ? subs.slice(0, 5).map(s => `
          <div style="display:flex;align-items:center;gap:12px;padding:10px 0;border-bottom:1px solid var(--border)">
            <div style="flex:1">
              <div style="font-size:13px;font-weight:600">${(s.milestone||'').replace('_',' ').replace(/\b\w/g,c=>c.toUpperCase())}</div>
              <div style="font-size:12px;color:var(--text-muted)">${utils.formatDate(s.created_at)}</div>
            </div>
            ${risk.badge(s.risk_level)}
            ${s.has_report
              ? `<button class="btn btn-sm btn-secondary" onclick="reports.download(${s.id})">📄 PDF</button>`
              : `<button class="btn btn-sm btn-ghost" onclick="reports.generate(${s.id})">Generate PDF</button>`}
          </div>
        `).join("") : `<div style="color:var(--text-muted);font-size:13px;padding:12px 0">No submissions yet</div>`}
      </div>
      <div class="modal-footer">
        ${roles.canSubmit(user) ? `<button class="btn btn-primary" onclick="modal.close(); submitPage.setProject(${p.id}); router.navigate('submit')">📸 Submit Photos</button>` : ''}
        ${roles.canEnforce(user) && p.status !== 'stop_work' ? `<button class="btn btn-danger" onclick="projectsPage.stopWork(${p.id})">🛑 Stop-Work Order</button>` : ''}
        <button class="btn btn-secondary" onclick="modal.close()">Close</button>
      </div>
    `);
  },

  showRegisterModal() {
    modal.show(`
      <div class="modal-header">
        <div class="modal-title">Register New Project</div>
        <button class="btn-close" onclick="modal.close()">✕</button>
      </div>
      <div class="modal-body">
        <div id="register-error"></div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Project Name *</label>
            <input class="form-input" id="r-name" placeholder="e.g. Lekki Phase 2 Residential">
          </div>
          <div class="form-group">
            <label class="form-label">Building Type *</label>
            <select class="form-select" id="r-type">
              <option value="residential">Residential</option>
              <option value="commercial">Commercial</option>
              <option value="industrial">Industrial</option>
              <option value="mixed">Mixed Use</option>
            </select>
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">Full Site Address *</label>
          <input class="form-input" id="r-address" placeholder="e.g. 42 Admiralty Way, Lekki Phase 1, Lagos">
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Number of Floors</label>
            <input class="form-input" id="r-floors" type="number" value="2" min="1" max="50">
          </div>
          <div class="form-group">
            <label class="form-label">Permit Reference</label>
            <input class="form-input" id="r-permit" placeholder="LASBCA permit no.">
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Start Date</label>
            <input class="form-input" id="r-start" type="date">
          </div>
          <div class="form-group">
            <label class="form-label">Expected Completion</label>
            <input class="form-input" id="r-end" type="date">
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">Description</label>
          <textarea class="form-textarea" id="r-desc" placeholder="Brief project description..."></textarea>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary" onclick="modal.close()">Cancel</button>
        <button class="btn btn-primary" id="register-btn" onclick="projectsPage.registerProject()">Register Project</button>
      </div>
    `);
  },

  async registerProject() {
    const btn = document.getElementById("register-btn");
    btn.disabled = true; btn.textContent = "Registering...";
    const errEl = document.getElementById("register-error");

    const body = {
      name:          document.getElementById("r-name").value.trim(),
      address:       document.getElementById("r-address").value.trim(),
      building_type: document.getElementById("r-type").value,
      floors:        parseInt(document.getElementById("r-floors").value) || 1,
      permit_ref:    document.getElementById("r-permit").value.trim(),
      description:   document.getElementById("r-desc").value.trim(),
      start_date:    document.getElementById("r-start").value || null,
      expected_end:  document.getElementById("r-end").value   || null,
    };

    const res = await api.post("/projects", body);
    if (res.ok) {
      modal.close();
      toast.success(`✅ Project registered! ID: ${res.data.project.sgid}`);
      await this.load();
    } else {
      errEl.innerHTML = `<div class="alert alert-error"><span>❌</span>${res.data.error}</div>`;
      btn.disabled = false; btn.textContent = "Register Project";
    }
  },

  async stopWork(projectId) {
    if (!confirm("Issue a stop-work order for this project? This will be visible to the developer and supervisor immediately.")) return;
    const res = await api.post(`/projects/${projectId}/stop-work`, {});
    if (res.ok) {
      toast.warning("🛑 Stop-work order issued");
      modal.close();
      await this.load();
    } else {
      toast.error(res.data.error);
    }
  }
};

/* ================================================================== */
/* SUBMIT PAGE                                                          */
/* ================================================================== */
const submitPage = {
  selectedFiles: [],
  preselectedProjectId: null,

  setProject(id) { this.preselectedProjectId = id; },

  async load() {
    const el = document.getElementById("submit-content");
    if (!el) return;

    // Load user's projects for the dropdown
    const res = await api.get("/projects?per_page=100");
    const projects = res.data.projects || [];

    const options = projects.map(p => `<option value="${p.id}" ${p.id === this.preselectedProjectId ? 'selected' : ''}>${p.sgid} — ${p.name}</option>`).join("");

    el.innerHTML = `
      <div class="section-header">
        <div>
          <div class="section-title">Submit Site Photos</div>
          <div class="section-sub">Upload 1–5 images for AI risk analysis</div>
        </div>
      </div>

      <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px">
        <div>
          <div class="card">
            <div class="card-header"><span class="card-title">📋 Submission Details</span></div>
            <div class="card-body">
              <div id="submit-error"></div>
              <div class="form-group">
                <label class="form-label">Select Project *</label>
                <select class="form-select" id="sub-project">
                  <option value="">— Choose a project —</option>
                  ${options}
                </select>
              </div>
              <div class="form-group">
                <label class="form-label">Construction Milestone *</label>
                <select class="form-select" id="sub-milestone">
                  <option value="foundation">Foundation</option>
                  <option value="column_casting">Column Casting</option>
                  <option value="lintel">Lintel Stage</option>
                  <option value="roofing">Roofing</option>
                  <option value="finishing">Finishing</option>
                  <option value="completion">Completion</option>
                  <option value="existing_building">Existing Building Health Check</option>
                </select>
              </div>
              <div class="form-group">
                <label class="form-label">Site Notes <span style="color:var(--text-muted)">(optional)</span></label>
                <textarea class="form-textarea" id="sub-notes" placeholder="Describe anything specific you want the AI to check..."></textarea>
              </div>
            </div>
          </div>
        </div>

        <div>
          <div class="card">
            <div class="card-header"><span class="card-title">📸 Upload Images (1–5)</span></div>
            <div class="card-body">
              <div class="dropzone" id="dropzone" onclick="document.getElementById('file-input').click()">
                <div class="dropzone-icon">📷</div>
                <div class="dropzone-text">Click or drag images here</div>
                <div class="dropzone-hint">JPG, PNG, WEBP · Max 20MB each</div>
              </div>
              <input type="file" id="file-input" accept="image/jpeg,image/png,image/webp" multiple style="display:none" onchange="submitPage.handleFiles(this.files)">
              <div id="image-previews" class="image-grid" style="margin-top:12px"></div>
            </div>
          </div>

          <button class="btn btn-primary btn-lg" id="submit-btn" onclick="submitPage.submit()" style="width:100%;margin-top:16px">
            🔍 Analyse Site
          </button>
        </div>
      </div>

      <div id="analysis-result" style="margin-top:24px"></div>
    `;

    // Drag-and-drop
    const dz = document.getElementById("dropzone");
    dz.addEventListener("dragover", e => { e.preventDefault(); dz.classList.add("drag-over"); });
    dz.addEventListener("dragleave", () => dz.classList.remove("drag-over"));
    dz.addEventListener("drop", e => {
      e.preventDefault(); dz.classList.remove("drag-over");
      this.handleFiles(e.dataTransfer.files);
    });
  },

  handleFiles(fileList) {
    const allowed = ["image/jpeg", "image/png", "image/webp"];
    for (const f of fileList) {
      if (!allowed.includes(f.type)) { toast.warning(`${f.name} is not a supported image type`); continue; }
      if (this.selectedFiles.length >= 5) { toast.warning("Maximum 5 images per submission"); break; }
      if (f.size > 20 * 1024 * 1024) { toast.warning(`${f.name} is too large (max 20MB)`); continue; }
      this.selectedFiles.push(f);
    }
    this.renderPreviews();
  },

  renderPreviews() {
    const container = document.getElementById("image-previews");
    if (!container) return;
    container.innerHTML = this.selectedFiles.map((f, i) => {
      const url = URL.createObjectURL(f);
      return `<div class="image-thumb">
        <img src="${url}" alt="Preview ${i+1}">
        <button class="remove-btn" onclick="submitPage.removeFile(${i})">✕</button>
      </div>`;
    }).join("");
  },

  removeFile(index) {
    this.selectedFiles.splice(index, 1);
    this.renderPreviews();
  },

  async submit() {
    const projectId  = document.getElementById("sub-project").value;
    const milestone  = document.getElementById("sub-milestone").value;
    const notes      = document.getElementById("sub-notes").value;
    const errEl      = document.getElementById("submit-error");
    const btn        = document.getElementById("submit-btn");
    const resultEl   = document.getElementById("analysis-result");

    if (!projectId) { errEl.innerHTML = `<div class="alert alert-warning"><span>⚠️</span>Please select a project</div>`; return; }
    if (this.selectedFiles.length === 0) { errEl.innerHTML = `<div class="alert alert-warning"><span>⚠️</span>Please upload at least one image</div>`; return; }

    errEl.innerHTML = "";
    btn.disabled = true;
    btn.innerHTML = `<div class="spinner"></div> Analysing with AI... (~30 seconds)`;
    resultEl.innerHTML = `<div class="loading-state"><div class="spinner spinner-lg"></div><p>AI is analysing your construction site images...</p></div>`;

    const form = new FormData();
    form.append("project_id", projectId);
    form.append("milestone",  milestone);
    form.append("notes",      notes);
    this.selectedFiles.forEach(f => form.append("images", f));

    const res = await api.upload("/analysis/submit", form);

    btn.disabled = false;
    btn.innerHTML = "🔍 Analyse Site";

    if (!res.ok) {
      errEl.innerHTML = `<div class="alert alert-error"><span>❌</span>${res.data.error || "Submission failed"}</div>`;
      resultEl.innerHTML = "";
      return;
    }

    const analysis = res.data.analysis;
    this.renderResult(resultEl, analysis, res.data.submission?.id);
    this.selectedFiles = [];
    this.renderPreviews();
    toast.success("Analysis complete!");
  },

  renderResult(el, analysis, submissionId) {
    if (!analysis) return;

    const bgMap = { safe: "#16a34a", monitor: "#d97706", high_risk: "#ea580c", critical: "#dc2626" };
    const bg    = bgMap[analysis.risk_level] || "#6b7280";
    const flags = analysis.flags || [];
    const recs  = analysis.recommendations || [];

    el.innerHTML = `
      <div class="card">
        <div class="risk-result-card" style="background:${bg};border-radius:var(--radius-md) var(--radius-md) 0 0">
          <div class="risk-result-header">
            <div>
              <div class="risk-result-score">${Math.round(analysis.risk_score || 0)}</div>
              <div style="font-size:12px;color:rgba(255,255,255,.7)">Risk Score / 100</div>
            </div>
            <div>
              <div class="risk-result-label">${risk.label(analysis.risk_level)}</div>
              <div class="risk-result-desc">${(flags.length || 0)} risk flag${flags.length !== 1 ? 's' : ''} detected</div>
              ${analysis.mode === 'demo' ? `<div style="font-size:11px;color:rgba(255,255,255,.6);margin-top:4px">⚙️ Demo mode — set ANTHROPIC_API_KEY for real AI</div>` : ''}
            </div>
          </div>
        </div>

        <div class="card-body">
          <div style="background:var(--bg-surface-2);border-radius:var(--radius-sm);padding:16px;margin-bottom:20px">
            <strong>📋 Inspector Summary</strong>
            <p style="margin-top:8px;font-size:14px;color:var(--text-secondary);line-height:1.6">${analysis.summary}</p>
          </div>

          ${flags.length ? `
            <strong>🚩 Risk Flags (${flags.length})</strong>
            <div style="margin-top:10px">
              ${flags.map(f => {
                const sevColour = { critical:"#ef4444", high:"#f97316", medium:"#f59e0b", low:"#22c55e" }[f.severity] || "#94a3b8";
                return `<div style="border-left:3px solid ${sevColour};padding:10px 14px;margin-bottom:10px;background:var(--bg-surface-2);border-radius:0 var(--radius-sm) var(--radius-sm) 0">
                  <div style="font-weight:600;font-size:13px">${f.category} <span style="color:${sevColour};font-size:11px;font-weight:700;text-transform:uppercase">${f.severity}</span></div>
                  <div style="font-size:13px;color:var(--text-secondary);margin-top:4px">${f.description}</div>
                </div>`;
              }).join("")}
            </div>
          ` : `<div class="alert alert-success"><span>✅</span>No structural risk flags detected in this submission</div>`}

          ${recs.length ? `
            <strong style="display:block;margin-top:16px">📌 Recommended Actions</strong>
            <ol style="margin-top:8px;padding-left:20px">
              ${recs.map(r => `<li style="font-size:14px;color:var(--text-secondary);margin-bottom:6px">${r}</li>`).join("")}
            </ol>
          ` : ""}
        </div>

        <div class="modal-footer" style="border-top:1px solid var(--border);padding:16px 20px;display:flex;gap:10px">
          ${submissionId ? `<button class="btn btn-secondary" onclick="reports.generate(${submissionId})">📄 Generate PDF Report</button>` : ""}
          <button class="btn btn-ghost" onclick="router.navigate('projects')">← Back to Projects</button>
        </div>
      </div>
    `;
  }
};

/* ================================================================== */
/* INSPECTION QUEUE PAGE (inspector / agency_admin only)               */
/* ================================================================== */
const inspectPage = {
  async load() {
    const el = document.getElementById("inspect-content");
    if (!el) return;

    el.innerHTML = `<div class="loading-state"><div class="spinner spinner-lg"></div><p>Loading inspection queue...</p></div>`;

    const res = await api.get("/admin/dashboard");
    if (!res.ok) { el.innerHTML = `<div class="alert alert-error"><span>❌</span>${res.data.error}</div>`; return; }

    const data     = res.data;
    const queue    = data.priority_queue || [];
    const overview = data.overview || {};

    const rows = queue.length ? queue.map((p, i) => `
      <tr>
        <td style="font-weight:700;color:var(--text-muted)">#${i+1}</td>
        <td><span style="font-family:monospace;font-size:12px;color:var(--brand-primary)">${p.sgid}</span></td>
        <td>
          <div style="font-weight:600">${p.name}</div>
          <div style="font-size:12px;color:var(--text-muted)">${p.address}</div>
        </td>
        <td>${risk.badge(p.risk_level)}</td>
        <td>
          <div class="risk-bar-wrap">
            <div class="risk-bar-track"><div class="risk-bar-fill ${risk.fillClass(p.risk_level)}" style="width:${p.risk_score || 0}%"></div></div>
            <div class="risk-bar-label">${Math.round(p.risk_score || 0)}</div>
          </div>
        </td>
        <td>${utils.statusBadge(p.status)}</td>
        <td>${utils.formatDate(p.updated_at)}</td>
        <td>
          <button class="btn btn-sm btn-secondary" onclick="projectsPage.viewProject(${p.id})">Inspect</button>
          ${roles.canEnforce(auth.getUser()) && p.status !== 'stop_work' ? `<button class="btn btn-sm btn-danger" style="margin-left:6px" onclick="projectsPage.stopWork(${p.id})">Stop</button>` : ''}
        </td>
      </tr>
    `).join("") : `<tr><td colspan="8"><div class="empty-state" style="padding:40px"><div class="empty-icon">✅</div><div class="empty-title">No flagged projects</div><div class="empty-desc">All sites are within acceptable risk levels</div></div></td></tr>`;

    el.innerHTML = `
      <div class="section-header">
        <div>
          <div class="section-title">🔍 Inspection Queue</div>
          <div class="section-sub">Priority-ranked high-risk sites requiring inspection</div>
        </div>
      </div>

      <div class="stat-grid" style="margin-bottom:24px">
        <div class="stat-card"><div class="stat-icon">🔴</div><div class="stat-label">Critical</div><div class="stat-value" style="color:var(--risk-critical)">${overview.critical || 0}</div></div>
        <div class="stat-card"><div class="stat-icon">🟠</div><div class="stat-label">High Risk</div><div class="stat-value" style="color:var(--risk-high)">${overview.high_risk || 0}</div></div>
        <div class="stat-card"><div class="stat-icon">🚨</div><div class="stat-label">Flagged</div><div class="stat-value">${overview.flagged || 0}</div></div>
        <div class="stat-card"><div class="stat-icon">🛑</div><div class="stat-label">Stop-Work</div><div class="stat-value" style="color:var(--risk-critical)">${overview.stop_work || 0}</div></div>
      </div>

      <div class="card">
        <div class="card-header"><span class="card-title">Priority Inspection Queue</span></div>
        <div class="table-wrap">
          <table>
            <thead><tr>
              <th>Rank</th><th>SGID</th><th>Project</th><th>Risk</th><th>Score</th><th>Status</th><th>Last Update</th><th>Actions</th>
            </tr></thead>
            <tbody>${rows}</tbody>
          </table>
        </div>
      </div>
    `;
  }
};

/* ================================================================== */
/* ANALYTICS PAGE (inspector / agency_admin)                           */
/* ================================================================== */
const analyticsPage = {
  async load() {
    const el = document.getElementById("analytics-content");
    if (!el) return;

    const res = await api.get("/admin/dashboard");
    if (!res.ok) { el.innerHTML = `<div class="alert alert-error"><span>❌</span>${res.data.error}</div>`; return; }

    const { overview, by_state } = res.data;

    const total = overview.total_projects || 1;
    const safeP   = Math.round((overview.safe       || 0) / total * 100);
    const monP    = Math.round(((total - (overview.safe||0) - (overview.high_risk||0) - (overview.critical||0))) / total * 100);
    const highP   = Math.round((overview.high_risk  || 0) / total * 100);
    const critP   = Math.round((overview.critical   || 0) / total * 100);

    el.innerHTML = `
      <div class="section-title" style="margin-bottom:20px">📊 Platform Analytics</div>

      <div class="stat-grid" style="margin-bottom:24px">
        <div class="stat-card"><div class="stat-icon">🏗️</div><div class="stat-label">Total Projects</div><div class="stat-value">${overview.total_projects || 0}</div></div>
        <div class="stat-card"><div class="stat-icon">📸</div><div class="stat-label">Total Submissions</div><div class="stat-value">${overview.total_submissions || 0}</div></div>
        <div class="stat-card"><div class="stat-icon">👥</div><div class="stat-label">Registered Users</div><div class="stat-value">${overview.total_users || 0}</div></div>
        <div class="stat-card"><div class="stat-icon">✅</div><div class="stat-label">Safe Sites</div><div class="stat-value" style="color:var(--risk-safe)">${overview.safe || 0}</div></div>
      </div>

      <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
        <div class="card">
          <div class="card-header"><span class="card-title">Risk Distribution</span></div>
          <div class="card-body">
            ${[
              ["safe",     "SAFE",      safeP, "var(--risk-safe)"],
              ["monitor",  "MONITOR",   monP,  "var(--risk-monitor)"],
              ["high",     "HIGH RISK", highP, "var(--risk-high)"],
              ["critical", "CRITICAL",  critP, "var(--risk-critical)"],
            ].map(([,label, pct, colour]) => `
              <div style="margin-bottom:14px">
                <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px">
                  <span style="font-weight:500">${label}</span>
                  <span style="color:var(--text-muted)">${pct}%</span>
                </div>
                <div class="risk-bar-track" style="height:10px">
                  <div style="height:100%;width:${pct}%;background:${colour};border-radius:4px;transition:width .6s ease"></div>
                </div>
              </div>
            `).join("")}
          </div>
        </div>

        <div class="card">
          <div class="card-header"><span class="card-title">Projects by State</span></div>
          <div class="card-body">
            ${(by_state || []).map(s => `
              <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--border)">
                <span style="font-size:14px;font-weight:500">${s.state || 'Unknown'}</span>
                <div style="display:flex;align-items:center;gap:8px">
                  <div class="risk-bar-track" style="width:100px;height:6px">
                    <div style="height:100%;width:${Math.min(100, (s.count/(overview.total_projects||1))*100)}%;background:var(--brand-primary);border-radius:4px"></div>
                  </div>
                  <span style="font-size:13px;font-weight:600;min-width:24px;text-align:right">${s.count}</span>
                </div>
              </div>
            `).join("") || `<div style="color:var(--text-muted)">No state data available</div>`}
          </div>
        </div>
      </div>
    `;
  }
};

/* ================================================================== */
/* USER MANAGEMENT (agency_admin only)                                 */
/* ================================================================== */
const usersPage = {
  async load() {
    const el = document.getElementById("users-content");
    if (!el) return;

    const res = await api.get("/admin/users");
    if (!res.ok) { el.innerHTML = `<div class="alert alert-error"><span>❌</span>${res.data.error}</div>`; return; }

    const users = res.data.users || [];
    const rows = users.map(u => `
      <tr>
        <td>
          <div style="display:flex;align-items:center;gap:10px">
            <div class="sidebar-avatar" style="width:32px;height:32px;font-size:12px">${utils.initials(u.name)}</div>
            <div>
              <div style="font-weight:600">${u.name}</div>
              <div style="font-size:12px;color:var(--text-muted)">${u.email}</div>
            </div>
          </div>
        </td>
        <td><span style="background:var(--bg-surface-2);padding:3px 10px;border-radius:20px;font-size:12px">${roles.label(u.role)}</span></td>
        <td>${u.organisation || '—'}</td>
        <td>${u.state || 'Lagos'}</td>
        <td><span style="color:${u.is_active ? 'var(--risk-safe)' : 'var(--risk-critical)'};font-weight:600">${u.is_active ? '● Active' : '● Inactive'}</span></td>
        <td>${utils.formatDate(u.created_at)}</td>
        <td>${u.is_active ? `<button class="btn btn-sm btn-danger" onclick="usersPage.deactivate(${u.id})">Deactivate</button>` : '—'}</td>
      </tr>
    `).join("");

    el.innerHTML = `
      <div class="section-header">
        <div>
          <div class="section-title">👥 User Management</div>
          <div class="section-sub">${users.length} registered users</div>
        </div>
      </div>
      <div class="card">
        <div class="table-wrap">
          <table>
            <thead><tr><th>User</th><th>Role</th><th>Organisation</th><th>State</th><th>Status</th><th>Joined</th><th>Actions</th></tr></thead>
            <tbody>${rows}</tbody>
          </table>
        </div>
      </div>
    `;
  },

  async deactivate(userId) {
    if (!confirm("Deactivate this user? They will no longer be able to log in.")) return;
    const res = await api.post(`/admin/users/${userId}/deactivate`, {});
    if (res.ok) { toast.warning("User deactivated"); await this.load(); }
    else toast.error(res.data.error);
  }
};

/* ================================================================== */
/* PROFILE PAGE                                                        */
/* ================================================================== */
const profilePage = {
  async load() {
    const el = document.getElementById("profile-content");
    if (!el) return;

    const res = await api.get("/auth/me");
    if (!res.ok) { el.innerHTML = `<div class="alert alert-error"><span>❌</span>Could not load profile</div>`; return; }

    const u = res.data.user;
    el.innerHTML = `
      <div class="section-title" style="margin-bottom:20px">👤 My Profile</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
        <div class="card">
          <div class="card-header"><span class="card-title">Account Details</span></div>
          <div class="card-body">
            <div style="text-align:center;margin-bottom:20px">
              <div class="sidebar-avatar" style="width:64px;height:64px;font-size:24px;margin:0 auto 10px">${utils.initials(u.name)}</div>
              <div style="font-size:18px;font-weight:700">${u.name}</div>
              <div style="color:var(--text-muted)">${roles.label(u.role)}</div>
            </div>
            <div style="display:grid;gap:12px">
              ${[
                ["Email",        u.email],
                ["Role",         roles.label(u.role)],
                ["State",        u.state || "Lagos"],
                ["Organisation", u.organisation || "—"],
                ["Licence No.",  u.licence_no || "—"],
                ["Member Since", utils.formatDate(u.created_at)],
                ["Last Login",   utils.formatDateTime(u.last_login)],
              ].map(([k,v]) => `
                <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--border)">
                  <span style="font-size:13px;color:var(--text-muted)">${k}</span>
                  <span style="font-size:13px;font-weight:500">${v}</span>
                </div>
              `).join("")}
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><span class="card-title">Change Password</span></div>
          <div class="card-body">
            <div id="pw-msg"></div>
            <div class="form-group">
              <label class="form-label">Current Password</label>
              <input class="form-input" type="password" id="pw-current">
            </div>
            <div class="form-group">
              <label class="form-label">New Password</label>
              <input class="form-input" type="password" id="pw-new">
            </div>
            <button class="btn btn-primary" onclick="profilePage.changePassword()">Update Password</button>
            <hr style="margin:20px 0;border:none;border-top:1px solid var(--border)">
            <button class="btn btn-danger" onclick="auth.logout()">Sign Out</button>
          </div>
        </div>
      </div>
    `;
  },

  async changePassword() {
    const msgEl = document.getElementById("pw-msg");
    const res   = await api.put("/auth/change-password", {
      current_password: document.getElementById("pw-current").value,
      new_password:     document.getElementById("pw-new").value,
    });
    if (res.ok) {
      msgEl.innerHTML = `<div class="alert alert-success"><span>✅</span>Password updated</div>`;
      document.getElementById("pw-current").value = "";
      document.getElementById("pw-new").value     = "";
    } else {
      msgEl.innerHTML = `<div class="alert alert-error"><span>❌</span>${res.data.error}</div>`;
    }
  }
};

/* ================================================================== */
/* REPORT HELPERS                                                       */
/* ================================================================== */
const reports = {
  async generate(submissionId) {
    toast.info("Generating PDF report...");
    const res = await api.post(`/reports/${submissionId}/generate`, {});
    if (res.ok) {
      toast.success("✅ PDF report generated!");
      const reportId = res.data.report?.id;
      if (reportId) this.download(reportId);
    } else {
      toast.error(res.data.error);
    }
  },

  download(reportId) {
    const token = auth.getToken();
    const a     = document.createElement("a");
    a.href      = `${CONFIG.API_BASE}/reports/${reportId}/download`;
    a.target    = "_blank";
    // Note: For authenticated downloads, in production use a signed URL or token in query param
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }
};

/* ================================================================== */
/* MODAL HELPER                                                         */
/* ================================================================== */
const modal = {
  show(html) {
    let backdrop = document.getElementById("modal-backdrop");
    if (!backdrop) {
      backdrop = document.createElement("div");
      backdrop.id = "modal-backdrop";
      backdrop.className = "modal-backdrop";
      backdrop.onclick = e => { if (e.target === backdrop) this.close(); };
      document.body.appendChild(backdrop);
    }
    backdrop.innerHTML = `<div class="modal">${html}</div>`;
    backdrop.style.display = "flex";
  },

  close() {
    const backdrop = document.getElementById("modal-backdrop");
    if (backdrop) backdrop.style.display = "none";
  }
};
