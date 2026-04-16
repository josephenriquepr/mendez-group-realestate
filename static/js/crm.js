/* ═══════════════════════════════════════════════════════════════
   ListaPro CRM  — crm.js
   ═══════════════════════════════════════════════════════════════ */

const STAGE_LABELS = {
  prospecto: "Prospecto",
  activo:    "Activo",
  oferta:    "Oferta",
  contrato:  "Contrato",
  cerrado:   "Cerrado",
};

const OPO_ETAPA_LABELS = {
  prospecto:       "Prospecto",
  contacto:        "Contacto",
  propuesta:       "Propuesta",
  negociacion:     "Negociación",
  cerrado_ganado:  "Cerrado ✓",
  cerrado_perdido: "Perdido ✗",
};

const TIPO_ICONS = {
  nota:         "📝",
  llamada:      "📞",
  visita:       "🏠",
  correo:       "✉️",
  reunion:      "🤝",
  mensaje_meta: "💬",
};

const STATUS_LABELS = {
  borrador:   { label: "Borrador",   cls: "status-draft" },
  enviando:   { label: "Enviando…",  cls: "status-sending" },
  completado: { label: "Completado", cls: "status-done" },
  error:      { label: "Error",      cls: "status-error" },
};

let _state = {
  contacts:          [],
  properties:        [],
  pipeline:          {},
  activities:        [],
  selectedContactId: null,
  propStage:         "",
  propSearch:        "",
  editContactId:     null,
};

let _charts = {};          // Chart.js instances
let _campaignPollTimer = null;
let _editOpoId = null;
let _editCampaignId = null;

/* ── Bootstrap ─────────────────────────────────────────────────── */

document.addEventListener("DOMContentLoaded", () => {
  setupNav();
  document.getElementById("dashboard-date").textContent =
    new Date().toLocaleDateString("es-PR", { weekday:"long", year:"numeric", month:"long", day:"numeric" });
  document.getElementById("af-fecha").value = new Date().toISOString().slice(0, 10);
  loadView("dashboard");
});

function setupNav() {
  document.querySelectorAll(".nav-item").forEach(btn => {
    btn.addEventListener("click", () => loadView(btn.dataset.view));
  });
  document.querySelectorAll(".stage-filter").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".stage-filter").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      _state.propStage = btn.dataset.stage;
      renderProperties();
    });
  });
}

async function loadView(name) {
  document.querySelectorAll(".nav-item").forEach(b => b.classList.remove("active"));
  document.querySelector(`.nav-item[data-view="${name}"]`)?.classList.add("active");
  document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
  document.getElementById(`view-${name}`)?.classList.add("active");

  if (name === "dashboard")     await loadDashboard();
  if (name === "contacts")      await loadContacts();
  if (name === "properties")    await loadProperties();
  if (name === "pipeline")      await loadPipeline();
  if (name === "oportunidades") await loadOportunidades();
  if (name === "activities")    await loadActivities();
  if (name === "campaigns")     await loadCampaigns();
  if (name === "analytics")     await loadAnalytics();
  if (name === "integrations")  await loadIntegrations();
}

/* ── API helpers ────────────────────────────────────────────────── */

async function api(method, path, body) {
  const opts = {
    method,
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  };
  const res = await fetch(`/api/crm${path}`, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

async function apiRaw(method, path, body) {
  // For non-/api/crm paths
  const opts = {
    method,
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  };
  const res = await fetch(path, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

/* ── Toast ──────────────────────────────────────────────────────── */

function showToast(msg, type = "success") {
  const el = document.createElement("div");
  el.className = `toast toast-${type}`;
  el.textContent = msg;
  document.getElementById("toast-container").appendChild(el);
  setTimeout(() => el.classList.add("toast-hide"), 3000);
  setTimeout(() => el.remove(), 3400);
}

/* ════════════════════════ DASHBOARD ════════════════════════════ */

async function loadDashboard() {
  try {
    const data = await api("GET", "/dashboard");
    renderDashboard(data);
  } catch (e) { console.error(e); }
}

function renderDashboard(d) {
  const totalPipeline = Object.values(d.pipeline_counts).reduce((s, v) => s + v, 0);
  document.getElementById("stats-grid").innerHTML = `
    <div class="stat-card">
      <div class="stat-label">Total Contactos</div>
      <div class="stat-value">${d.total_contacts}</div>
      <div class="stat-sub">en el CRM</div>
    </div>
    <div class="stat-card accent">
      <div class="stat-label">Propiedades</div>
      <div class="stat-value">${d.total_properties}</div>
      <div class="stat-sub">guardadas</div>
    </div>
    <div class="stat-card success">
      <div class="stat-label">Cerrados</div>
      <div class="stat-value">${d.pipeline_counts.cerrado || 0}</div>
      <div class="stat-sub">$${fmtMoney(d.closed_value)}</div>
    </div>
    <div class="stat-card warning">
      <div class="stat-label">En Pipeline</div>
      <div class="stat-value">${totalPipeline}</div>
      <div class="stat-sub">activos total</div>
    </div>
  `;

  const fl = document.getElementById("followups-list");
  if (!d.upcoming_followups.length) {
    fl.innerHTML = `<div class="empty-state"><p>Sin follow-ups próximos</p></div>`;
  } else {
    fl.innerHTML = d.upcoming_followups.map(c => {
      const diff = daysDiff(c.follow_up_date);
      const urgentClass = diff <= 1 ? " urgent" : "";
      const label = diff === 0 ? "Hoy" : diff === 1 ? "Mañana" : `${c.follow_up_date}`;
      return `<div class="followup-item" onclick="loadView('contacts');selectContact(${c.id})">
        <div class="contact-avatar avatar-${c.tipo}">${c.nombre[0].toUpperCase()}</div>
        <div>
          <div class="followup-name">${esc(c.nombre)}</div>
          <div class="followup-date${urgentClass}">📅 ${label}</div>
        </div>
      </div>`;
    }).join("");
  }

  const al = document.getElementById("recent-activities-list");
  if (!d.recent_activities.length) {
    al.innerHTML = `<div class="empty-state"><p>Sin actividades recientes</p></div>`;
  } else {
    al.innerHTML = d.recent_activities.map(a => renderActivityItem(a, false)).join("");
  }
}

/* ════════════════════════ CONTACTS ═════════════════════════════ */

async function loadContacts(q = "") {
  try {
    _state.contacts = await api("GET", `/contacts?q=${encodeURIComponent(q)}`);
    renderContactsList();
  } catch (e) { console.error(e); }
}

function searchContacts(q) {
  clearTimeout(window._contactSearchTimer);
  window._contactSearchTimer = setTimeout(() => loadContacts(q), 280);
}

function renderContactsList() {
  const el = document.getElementById("contacts-list");
  if (!_state.contacts.length) {
    el.innerHTML = `<div class="empty-state"><p>Sin contactos</p><small>Crea tu primer contacto</small></div>`;
    return;
  }
  el.innerHTML = _state.contacts.map(c => {
    const sourceIcon = c.fuente === "instagram" ? "📸" : c.fuente === "facebook" ? "👍" : "";
    return `
    <div class="contact-row${_state.selectedContactId === c.id ? " selected" : ""}"
         onclick="selectContact(${c.id})">
      <div class="contact-avatar avatar-${c.tipo}">${c.nombre[0].toUpperCase()}</div>
      <div class="contact-row-info">
        <div class="contact-row-name">${esc(c.nombre)} ${sourceIcon}</div>
        <div class="contact-row-sub">${esc(c.telefono || c.email || "—")}</div>
      </div>
      <span class="tipo-badge tipo-${c.tipo}">${c.tipo}</span>
    </div>`;
  }).join("");
}

async function selectContact(id) {
  _state.selectedContactId = id;
  renderContactsList();
  try {
    const c = await api("GET", `/contacts/${id}`);
    renderContactDetail(c);
  } catch (e) { console.error(e); }
}

function renderContactDetail(c) {
  const el = document.getElementById("contact-detail");
  el.style.display = "block";

  const fu = c.follow_up_date
    ? `<span style="color:var(--accent);font-weight:700;">📅 ${c.follow_up_date}</span>`
    : `<span style="color:var(--text-muted);">—</span>`;

  const sourceHtml = c.fuente && c.fuente !== "manual"
    ? `<span class="source-badge source-${c.fuente}">${c.fuente === "instagram" ? "📸 Instagram" : "👍 Facebook"}</span>`
    : "";

  // Quick actions
  const phone = c.telefono ? c.telefono.replace(/\D/g, "") : "";
  const quickActions = `
    <div class="quick-actions">
      ${c.telefono ? `<a class="qa-btn qa-call" href="tel:${esc(c.telefono)}" title="Llamar">📞 Llamar</a>` : ""}
      ${phone ? `<a class="qa-btn qa-whatsapp" href="https://wa.me/${phone}" target="_blank" title="WhatsApp">💬 WhatsApp</a>` : ""}
      ${c.email ? `<a class="qa-btn qa-email" href="mailto:${esc(c.email)}" title="Email">✉️ Email</a>` : ""}
      <button class="qa-btn qa-oportunidad" onclick="openOpoModal(null, ${c.id})">💡 Oportunidad</button>
      <button class="qa-btn qa-actividad" onclick="_prefillActivity(${c.id});openActivityModal()">📝 Actividad</button>
    </div>`;

  // Tags
  const tagsHtml = `
    <div class="contact-tags-row" id="tags-row-${c.id}">
      ${(c.tags || []).map(t =>
        `<span class="tag-pill" style="background:${t.color}20;color:${t.color};border-color:${t.color}40;">
           ${esc(t.nombre)}
           <button class="tag-remove" onclick="removeTagFromContact(${c.id},${t.id})">×</button>
         </span>`
      ).join("")}
      <button class="tag-add-btn" onclick="openTagPicker(${c.id})">+ Tag</button>
    </div>`;

  // Properties
  const propsHtml = (c.properties || []).length
    ? c.properties.map(p => `
        <div class="mini-prop-card" onclick="openPropertyDetail(${p.id})">
          ${p.foto_portada_url
            ? `<img class="mini-prop-thumb" src="${p.foto_portada_url}" />`
            : `<div class="mini-prop-thumb no-img">🏡</div>`}
          <div class="mini-prop-info">
            <div class="mini-prop-addr">${esc(p.direccion)}</div>
            <div class="mini-prop-sub">$${fmtMoney(p.precio)} · <span class="tipo-badge tipo-${p.stage}" style="font-size:10px;">${STAGE_LABELS[p.stage]}</span></div>
          </div>
        </div>`).join("")
    : `<div style="color:var(--text-muted);font-size:13px;">Sin propiedades asociadas</div>`;

  // Oportunidades
  const OPO_COLORS = { prospecto:"#1565c0", contacto:"#0277bd", propuesta:"#f57f17",
    negociacion:"#ad1457", cerrado_ganado:"#2e7d32", cerrado_perdido:"#757575" };
  const oposHtml = (c.oportunidades || []).length
    ? c.oportunidades.map(o => `
        <div class="mini-opo-card" onclick="openOpoModal(${o.id}, ${c.id})">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span class="opo-etapa-dot" style="background:${OPO_COLORS[o.etapa]||'#999'};"></span>
            <span style="font-size:11px;color:#fff;background:${OPO_COLORS[o.etapa]||'#999'};padding:2px 8px;border-radius:8px;">${OPO_ETAPA_LABELS[o.etapa]||o.etapa}</span>
          </div>
          <div class="mini-opo-nombre">${esc(o.nombre)}</div>
          <div class="mini-opo-valor">$${fmtMoney(o.valor)} · ${o.probabilidad}%</div>
        </div>`).join("")
    : `<div style="color:var(--text-muted);font-size:13px;">Sin oportunidades</div>`;

  // Tasks
  const tasksHtml = (c.tasks || []).length
    ? c.tasks.map(t => `
        <div class="task-item${t.completada ? " task-done" : ""}" id="task-${t.id}">
          <input type="checkbox" class="task-check" ${t.completada ? "checked" : ""}
                 onchange="toggleTask(${t.id}, this.checked, ${c.id})" />
          <div class="task-body">
            <div class="task-titulo">${esc(t.titulo)}</div>
            ${t.fecha_vencimiento ? `<div class="task-fecha">📅 ${t.fecha_vencimiento}</div>` : ""}
          </div>
          <button class="task-del" onclick="deleteTask(${t.id}, ${c.id})">✕</button>
        </div>`).join("")
    : `<div style="color:var(--text-muted);font-size:13px;">Sin tareas</div>`;

  // Activities
  const actsHtml = (c.activities || []).length
    ? c.activities.slice(0, 6).map(a => renderActivityItem(a, false)).join("")
    : `<div style="color:var(--text-muted);font-size:13px;padding:8px 0;">Sin actividades</div>`;

  el.innerHTML = `
    <div class="contact-detail-header">
      <div style="flex:1;min-width:0;">
        <div class="contact-detail-name">${esc(c.nombre)}</div>
        <div class="contact-detail-tipo" style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-top:4px;">
          <span class="tipo-badge tipo-${c.tipo}">${c.tipo}</span>
          ${sourceHtml}
        </div>
      </div>
      <div class="contact-detail-actions">
        <button class="btn-secondary btn-sm" onclick="openContactModal(${c.id})">Editar</button>
        <button class="btn-danger btn-sm" onclick="deleteContact(${c.id})">Eliminar</button>
      </div>
    </div>

    ${quickActions}

    <div class="contact-info-grid">
      <div class="contact-info-item">
        <div class="contact-info-label">Teléfono</div>
        <div class="contact-info-value">${esc(c.telefono || "—")}</div>
      </div>
      <div class="contact-info-item">
        <div class="contact-info-label">Email</div>
        <div class="contact-info-value">${esc(c.email || "—")}</div>
      </div>
      <div class="contact-info-item" style="grid-column:1/-1;">
        <div class="contact-info-label">Próximo Follow-up</div>
        <div class="contact-info-value">${fu}</div>
      </div>
    </div>

    <div class="contact-detail-section">
      <h4>Tags</h4>
      ${tagsHtml}
    </div>

    ${c.notas ? `
    <div class="contact-detail-section">
      <h4>Notas</h4>
      <div class="contact-notes">${esc(c.notas)}</div>
    </div>` : ""}

    <div class="contact-detail-section">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
        <h4 style="margin:0;">Tareas (${(c.tasks||[]).filter(t=>!t.completada).length} pendientes)</h4>
        <button class="btn-secondary btn-sm" onclick="openTaskModal(${c.id})">+ Tarea</button>
      </div>
      <div id="tasks-container-${c.id}">${tasksHtml}</div>
    </div>

    <div class="contact-detail-section">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
        <h4 style="margin:0;">Oportunidades (${(c.oportunidades||[]).length})</h4>
        <button class="btn-secondary btn-sm" onclick="openOpoModal(null, ${c.id})">+ Oportunidad</button>
      </div>
      ${oposHtml}
    </div>

    <div class="contact-detail-section">
      <h4>Propiedades (${(c.properties||[]).length})</h4>
      ${propsHtml}
    </div>

    <div class="contact-detail-section">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
        <h4 style="margin:0;">Actividades recientes</h4>
        <button class="btn-secondary btn-sm" onclick="_prefillActivity(${c.id});openActivityModal()">+ Actividad</button>
      </div>
      ${actsHtml}
    </div>
  `;
}

/* Contact CRUD */

let _editContactId = null;

function openContactModal(id = null) {
  _editContactId = id;
  document.getElementById("contact-modal-title").textContent = id ? "Editar Contacto" : "Nuevo Contacto";
  if (id) {
    const c = _state.contacts.find(x => x.id === id);
    if (c) {
      document.getElementById("cf-nombre").value   = c.nombre   || "";
      document.getElementById("cf-telefono").value = c.telefono || "";
      document.getElementById("cf-email").value    = c.email    || "";
      document.getElementById("cf-tipo").value     = c.tipo     || "prospecto";
      document.getElementById("cf-followup").value = c.follow_up_date || "";
      document.getElementById("cf-notas").value    = c.notas    || "";
    }
  } else {
    document.getElementById("contact-form").reset();
  }
  document.getElementById("contact-modal").style.display = "flex";
}

async function submitContactForm(e) {
  e.preventDefault();
  const body = {
    nombre:         document.getElementById("cf-nombre").value.trim(),
    telefono:       document.getElementById("cf-telefono").value.trim(),
    email:          document.getElementById("cf-email").value.trim(),
    tipo:           document.getElementById("cf-tipo").value,
    follow_up_date: document.getElementById("cf-followup").value || null,
    notas:          document.getElementById("cf-notas").value.trim(),
  };
  try {
    if (_editContactId) {
      await api("PATCH", `/contacts/${_editContactId}`, body);
      showToast("Contacto actualizado");
    } else {
      await api("POST", "/contacts", body);
      showToast("Contacto creado");
    }
    closeModal("contact-modal");
    await loadContacts(document.getElementById("contact-search").value);
    if (_state.selectedContactId) selectContact(_state.selectedContactId);
  } catch (err) { showToast("Error: " + err.message, "error"); }
}

async function deleteContact(id) {
  if (!confirm("¿Eliminar este contacto y todas sus propiedades y actividades?")) return;
  await api("DELETE", `/contacts/${id}`);
  _state.selectedContactId = null;
  document.getElementById("contact-detail").style.display = "none";
  await loadContacts();
  showToast("Contacto eliminado", "info");
}

/* ════════════════════════ PROPERTIES ═══════════════════════════ */

async function loadProperties() {
  try {
    _state.properties = await api("GET", "/properties");
    renderProperties();
  } catch (e) { console.error(e); }
}

function filterProperties() {
  _state.propSearch = document.getElementById("prop-search").value.toLowerCase();
  renderProperties();
}

function renderProperties() {
  let props = _state.properties;
  if (_state.propStage) props = props.filter(p => p.stage === _state.propStage);
  if (_state.propSearch) {
    const q = _state.propSearch;
    props = props.filter(p =>
      (p.direccion + p.pueblo + p.tipo_propiedad).toLowerCase().includes(q));
  }
  const el = document.getElementById("properties-grid");
  if (!props.length) {
    el.innerHTML = `<div class="empty-state" style="grid-column:1/-1;"><p>Sin propiedades</p></div>`;
    return;
  }
  el.innerHTML = props.map(p => propCard(p)).join("");
}

function propCard(p) {
  const thumb = p.foto_portada_url
    ? `<img class="prop-card-img" src="${p.foto_portada_url}" loading="lazy" />`
    : `<div class="prop-card-img" style="display:flex;align-items:center;justify-content:center;font-size:40px;">🏡</div>`;
  const contact = p.contact_id
    ? `<div class="prop-card-contact">👤 Cargando…</div>`
    : `<div class="prop-card-contact" style="opacity:0.5;">Sin contacto</div>`;
  return `
    <div class="prop-card" onclick="openPropertyDetail(${p.id})">
      ${thumb}
      <div class="prop-card-body">
        <span class="prop-card-stage stage-${p.stage}">${STAGE_LABELS[p.stage]}</span>
        <div class="prop-card-addr">${esc(p.direccion)}</div>
        <div class="prop-card-sub">${esc(p.tipo_propiedad)} · ${esc(p.pueblo)}</div>
        <div class="prop-card-price">$${fmtMoney(p.precio)}</div>
        ${contact}
      </div>
    </div>`;
}

async function openPropertyDetail(id) {
  try {
    const p = await api("GET", `/properties/${id}`);
    renderPropertyModal(p);
    document.getElementById("property-modal").style.display = "flex";
  } catch (e) { console.error(e); }
}

function renderPropertyModal(p) {
  document.getElementById("pm-title").textContent = p.direccion;

  const statsHtml = [
    p.habitaciones     ? `<div class="pm-stat"><div class="pm-stat-val">${p.habitaciones}</div><div class="pm-stat-lbl">Cuartos</div></div>` : "",
    p.banos != null    ? `<div class="pm-stat"><div class="pm-stat-val">${p.banos}</div><div class="pm-stat-lbl">Baños</div></div>` : "",
    p.pies_cuadrados   ? `<div class="pm-stat"><div class="pm-stat-val">${fmtNum(p.pies_cuadrados)}</div><div class="pm-stat-lbl">Sq Ft</div></div>` : "",
    p.estacionamientos ? `<div class="pm-stat"><div class="pm-stat-val">${p.estacionamientos}</div><div class="pm-stat-lbl">Estac.</div></div>` : "",
  ].filter(Boolean).join("");

  const stageButtons = Object.keys(STAGE_LABELS).map(s =>
    `<button class="pm-stage-btn${p.stage === s ? " current" : ""}"
             onclick="updateStage(${p.id}, '${s}', this)">${STAGE_LABELS[s]}</button>`
  ).join("");

  const links = [
    p.pdf_url ? `<a class="pm-link pm-link-pdf" href="${p.pdf_url}" target="_blank">📄 PDF</a>` : "",
    p.instagram_image_url ? `<a class="pm-link pm-link-ig" href="${p.instagram_image_url}" target="_blank">📸 Imagen IG</a>` : "",
  ].filter(Boolean).join("");

  const contactHtml = p.contact
    ? `<span onclick="closeModal('property-modal');loadView('contacts');selectContact(${p.contact.id})"
             style="cursor:pointer;color:var(--primary);font-weight:600;">
         👤 ${esc(p.contact.nombre)}
       </span>`
    : `<span style="color:var(--text-muted);">Sin contacto asignado</span>`;

  document.getElementById("property-modal-body").innerHTML = `
    ${p.foto_portada_url ? `<img class="pm-image" src="${p.foto_portada_url}" />` : ""}
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;flex-wrap:wrap;gap:8px;">
      <div style="font-size:20px;font-weight:800;color:var(--primary-dark);">$${fmtMoney(p.precio)}</div>
      <div>${contactHtml}</div>
    </div>
    <div style="margin-bottom:14px;font-size:13px;color:var(--text-muted);">
      ${esc(p.tipo_propiedad)} en ${esc(p.operacion)} · ${esc(p.pueblo)}, PR
    </div>

    ${statsHtml ? `<div class="pm-grid">${statsHtml}</div>` : ""}

    <div class="pm-section-label">Estado del Pipeline</div>
    <div class="pm-stage-row">${stageButtons}</div>

    <div class="pm-section-label">Notas CRM</div>
    <textarea id="pm-notas" rows="3" style="width:100%;padding:9px 12px;border:1.5px solid var(--border);border-radius:7px;font-size:13px;font-family:inherit;resize:vertical;"
      onchange="updatePropertyNotes(${p.id}, this.value)">${esc(p.notas_crm || "")}</textarea>

    ${p.listing_description ? `
      <div class="pm-section-label">Descripción Profesional</div>
      <div class="pm-text">${esc(p.listing_description)}</div>` : ""}

    ${links ? `<div class="pm-links">${links}</div>` : ""}

    <div style="margin-top:16px;display:flex;justify-content:space-between;align-items:center;">
      <button class="btn-danger btn-sm" onclick="deleteProperty(${p.id})">Eliminar</button>
      <div style="font-size:12px;color:var(--text-muted);">
        Guardado: ${p.created_at ? new Date(p.created_at).toLocaleDateString("es-PR") : "—"}
      </div>
    </div>
  `;
}

async function updateStage(propertyId, stage, btn) {
  try {
    await api("PATCH", `/properties/${propertyId}`, { stage });
    document.querySelectorAll(".pm-stage-btn").forEach(b => b.classList.remove("current"));
    btn.classList.add("current");
    await loadProperties();
    if (document.getElementById("view-pipeline").classList.contains("active")) loadPipeline();
  } catch (e) { showToast("Error: " + e.message, "error"); }
}

async function updatePropertyNotes(propertyId, notas_crm) {
  try { await api("PATCH", `/properties/${propertyId}`, { notas_crm }); } catch (_) {}
}

async function deleteProperty(id) {
  if (!confirm("¿Eliminar esta propiedad del CRM?")) return;
  await api("DELETE", `/properties/${id}`);
  closeModal("property-modal");
  await loadProperties();
  showToast("Propiedad eliminada", "info");
}

/* ════════════════════════ PIPELINE ═════════════════════════════ */

async function loadPipeline() {
  try {
    _state.pipeline = await api("GET", "/pipeline");
    renderPipeline();
  } catch (e) { console.error(e); }
}

function renderPipeline() {
  const stages = ["prospecto", "activo", "oferta", "contrato", "cerrado"];
  const board = document.getElementById("kanban-board");
  board.innerHTML = stages.map(stage => {
    const cards = (_state.pipeline[stage] || []);
    const cardsHtml = cards.map(p => {
      const nextStages = stages.filter(s => s !== stage);
      const moveBtns = nextStages.map(s =>
        `<button class="kanban-move-btn" onclick="event.stopPropagation();moveCard(${p.id},'${s}')">→ ${STAGE_LABELS[s]}</button>`
      ).join("");
      return `
        <div class="kanban-card" onclick="openPropertyDetail(${p.id})">
          <div class="kanban-card-addr">${esc(p.direccion)}</div>
          <div class="kanban-card-price">$${fmtMoney(p.precio)}</div>
          <div class="kanban-card-sub">${esc(p.tipo_propiedad)} · ${esc(p.pueblo)}</div>
          <div class="kanban-card-actions">${moveBtns}</div>
        </div>`;
    }).join("") || `<div style="color:var(--text-muted);font-size:12px;padding:8px 4px;">Vacío</div>`;

    return `
      <div class="kanban-col" data-stage="${stage}">
        <div class="kanban-col-header">
          ${STAGE_LABELS[stage]}
          <span class="kanban-count">${cards.length}</span>
        </div>
        <div class="kanban-cards">${cardsHtml}</div>
      </div>`;
  }).join("");
}

async function moveCard(propertyId, stage) {
  try {
    await api("PATCH", `/properties/${propertyId}`, { stage });
    await loadPipeline();
  } catch (e) { showToast("Error: " + e.message, "error"); }
}

/* ════════════════════════ OPORTUNIDADES ════════════════════════ */

async function loadOportunidades() {
  try {
    const data = await apiRaw("GET", "/api/crm/oportunidades/pipeline");
    renderOpoPipeline(data);
  } catch (e) { console.error(e); }
}

function renderOpoPipeline(data) {
  const { pipeline, totals } = data;

  // Summary bar
  const activeValue = Object.entries(totals)
    .filter(([k]) => !k.includes("perdido"))
    .reduce((s, [, v]) => s + v, 0);
  document.getElementById("opo-pipeline-summary").innerHTML = `
    <div class="opo-summary-bar">
      <div class="opo-summary-item">
        <div class="opo-summary-val">$${fmtMoney(activeValue)}</div>
        <div class="opo-summary-lbl">Pipeline Total</div>
      </div>
      <div class="opo-summary-item">
        <div class="opo-summary-val" style="color:var(--success);">$${fmtMoney(totals.cerrado_ganado || 0)}</div>
        <div class="opo-summary-lbl">Ganado</div>
      </div>
      <div class="opo-summary-item">
        <div class="opo-summary-val" style="color:var(--danger);">$${fmtMoney(totals.cerrado_perdido || 0)}</div>
        <div class="opo-summary-lbl">Perdido</div>
      </div>
    </div>`;

  const etapas = ["prospecto", "contacto", "propuesta", "negociacion", "cerrado_ganado", "cerrado_perdido"];
  document.getElementById("opo-kanban").innerHTML = etapas.map(etapa => {
    const cards = (pipeline[etapa] || []);
    const cardsHtml = cards.map(op => `
      <div class="opo-card" onclick="openOpoModal(${op.id})">
        <div class="opo-card-nombre">${esc(op.nombre)}</div>
        <div class="opo-card-valor">$${fmtMoney(op.valor)}</div>
        ${op.contacto_nombre ? `<div class="opo-card-contact">👤 ${esc(op.contacto_nombre)}</div>` : ""}
        <div class="opo-card-prob">
          <div class="prob-bar"><div class="prob-fill" style="width:${op.probabilidad}%"></div></div>
          <span>${op.probabilidad}%</span>
        </div>
        <div class="opo-card-actions" onclick="event.stopPropagation()">
          ${etapa !== "cerrado_ganado"  ? `<button class="opo-btn-won"  onclick="closeOpo(${op.id},'won')">✓ Ganado</button>` : ""}
          ${etapa !== "cerrado_perdido" ? `<button class="opo-btn-lost" onclick="closeOpo(${op.id},'lost')">✗ Perdido</button>` : ""}
        </div>
      </div>`).join("") || `<div style="color:var(--text-muted);font-size:12px;padding:8px 4px;">Vacío</div>`;

    return `
      <div class="opo-col" data-etapa="${etapa}">
        <div class="opo-col-header">
          ${OPO_ETAPA_LABELS[etapa]}
          <span class="kanban-count">${cards.length}</span>
        </div>
        <div class="opo-col-value">$${fmtMoney(totals[etapa] || 0)}</div>
        <div class="kanban-cards">${cardsHtml}</div>
      </div>`;
  }).join("");
}

async function closeOpo(id, result) {
  try {
    await apiRaw("POST", `/api/crm/oportunidades/${id}/close-${result}`);
    showToast(result === "won" ? "¡Oportunidad ganada!" : "Marcada como perdida", result === "won" ? "success" : "info");
    await loadOportunidades();
  } catch (e) { showToast("Error: " + e.message, "error"); }
}

async function openOpoModal(id = null, prefillContactId = null) {
  _editOpoId = id;
  document.getElementById("opo-modal-title").textContent = id ? "Editar Oportunidad" : "Nueva Oportunidad";

  // Load contacts for dropdown
  try {
    const contacts = await api("GET", "/contacts");
    document.getElementById("of-contacto-id").innerHTML =
      `<option value="">Sin contacto</option>` +
      contacts.map(c => `<option value="${c.id}">${esc(c.nombre)}</option>`).join("");
  } catch (_) {}

  if (id) {
    try {
      const op = await apiRaw("GET", `/api/crm/oportunidades/${id}`);
      document.getElementById("of-nombre").value       = op.nombre || "";
      document.getElementById("of-valor").value        = op.valor || 0;
      document.getElementById("of-probabilidad").value = op.probabilidad || 20;
      document.getElementById("of-etapa").value        = op.etapa || "prospecto";
      document.getElementById("of-cierre").value       = op.fecha_cierre_esperada || "";
      document.getElementById("of-contacto-id").value  = op.contacto_id || "";
      document.getElementById("of-notas").value        = op.notas || "";
    } catch (_) {}
  } else {
    document.getElementById("opo-form").reset();
    if (prefillContactId) {
      document.getElementById("of-contacto-id").value = prefillContactId;
    }
  }
  document.getElementById("opo-modal").style.display = "flex";
}

async function submitOpoForm(e) {
  e.preventDefault();
  const body = {
    nombre:               document.getElementById("of-nombre").value.trim(),
    valor:                parseFloat(document.getElementById("of-valor").value) || 0,
    etapa:                document.getElementById("of-etapa").value,
    probabilidad:         parseInt(document.getElementById("of-probabilidad").value) || 20,
    fecha_cierre_esperada: document.getElementById("of-cierre").value || null,
    contacto_id:          parseInt(document.getElementById("of-contacto-id").value) || null,
    notas:                document.getElementById("of-notas").value.trim(),
  };
  try {
    if (_editOpoId) {
      await apiRaw("PATCH", `/api/crm/oportunidades/${_editOpoId}`, body);
      showToast("Oportunidad actualizada");
    } else {
      await apiRaw("POST", "/api/crm/oportunidades", body);
      showToast("Oportunidad creada");
    }
    closeModal("opo-modal");
    await loadOportunidades();
  } catch (err) { showToast("Error: " + err.message, "error"); }
}

/* ════════════════════════ TAGS ═════════════════════════════════ */

let _allTags = [];

async function loadAllTags() {
  try {
    const data = await apiRaw("GET", "/api/crm/tags");
    _allTags = data.items;
    return _allTags;
  } catch (_) { return []; }
}

async function openTagPicker(contactId) {
  const tags = await loadAllTags();
  const contact = await api("GET", `/contacts/${contactId}`).catch(() => null);
  const assignedIds = new Set((contact?.tags || []).map(t => t.id));

  const el = document.getElementById("tag-picker-content");
  el.innerHTML = `
    <div style="margin-bottom:12px;">
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px;">
        ${tags.map(t => `
          <span class="tag-pill${assignedIds.has(t.id) ? " tag-assigned" : ""}"
                style="background:${t.color}20;color:${t.color};border-color:${t.color}40;cursor:pointer;"
                onclick="toggleContactTag(${contactId}, ${t.id}, ${assignedIds.has(t.id)}, this)">
            ${esc(t.nombre)}
          </span>`).join("")}
        ${!tags.length ? `<div style="color:var(--text-muted);font-size:13px;">Sin tags. Crea uno primero.</div>` : ""}
      </div>
      <div style="display:flex;gap:8px;margin-top:8px;">
        <input type="text" id="new-tag-name" class="search-input" style="flex:1;"
               placeholder="Nueva tag…" onkeydown="if(event.key==='Enter')createAndAssignTag(${contactId})" />
        <input type="color" id="new-tag-color" value="#1a6b8a" style="width:38px;height:38px;border:1.5px solid var(--border);border-radius:7px;cursor:pointer;padding:2px;" />
        <button class="btn-primary btn-sm" onclick="createAndAssignTag(${contactId})">Crear</button>
      </div>
    </div>`;

  document.getElementById("tag-picker-modal").style.display = "flex";
  document.getElementById("tag-picker-modal")._contactId = contactId;
}

async function toggleContactTag(contactId, tagId, isAssigned, el) {
  try {
    if (isAssigned) {
      await apiRaw("DELETE", `/api/crm/tags/contacts/${contactId}/${tagId}`);
      el.classList.remove("tag-assigned");
    } else {
      await apiRaw("POST", `/api/crm/tags/contacts/${contactId}/${tagId}`);
      el.classList.add("tag-assigned");
    }
    await selectContact(contactId);
  } catch (e) { showToast("Error: " + e.message, "error"); }
}

async function removeTagFromContact(contactId, tagId) {
  try {
    await apiRaw("DELETE", `/api/crm/tags/contacts/${contactId}/${tagId}`);
    await selectContact(contactId);
  } catch (e) { showToast("Error", "error"); }
}

async function createAndAssignTag(contactId) {
  const name = document.getElementById("new-tag-name")?.value.trim();
  const color = document.getElementById("new-tag-color")?.value || "#1a6b8a";
  if (!name) return;
  try {
    const tag = await apiRaw("POST", "/api/crm/tags", { nombre: name, color });
    await apiRaw("POST", `/api/crm/tags/contacts/${contactId}/${tag.id}`);
    showToast(`Tag "${name}" creada y asignada`);
    await openTagPicker(contactId);
    await selectContact(contactId);
  } catch (e) { showToast("Error: " + e.message, "error"); }
}

/* ════════════════════════ TASKS ════════════════════════════════ */

let _taskContactId = null;

function openTaskModal(contactId) {
  _taskContactId = contactId;
  document.getElementById("task-form").reset();
  document.getElementById("tf-fecha").value = "";
  document.getElementById("task-modal").style.display = "flex";
}

async function submitTaskForm(e) {
  e.preventDefault();
  const body = {
    contact_id:        _taskContactId,
    titulo:            document.getElementById("tf-titulo").value.trim(),
    descripcion:       document.getElementById("tf-descripcion").value.trim(),
    fecha_vencimiento: document.getElementById("tf-fecha").value || null,
  };
  try {
    await apiRaw("POST", "/api/crm/tasks", body);
    showToast("Tarea creada");
    closeModal("task-modal");
    await selectContact(_taskContactId);
  } catch (err) { showToast("Error: " + err.message, "error"); }
}

async function toggleTask(taskId, completada, contactId) {
  try {
    await apiRaw("PATCH", `/api/crm/tasks/${taskId}`, { completada });
    await selectContact(contactId);
  } catch (e) { showToast("Error", "error"); }
}

async function deleteTask(taskId, contactId) {
  try {
    await apiRaw("DELETE", `/api/crm/tasks/${taskId}`);
    await selectContact(contactId);
  } catch (e) { showToast("Error", "error"); }
}

/* ════════════════════════ CONTACT FILTERS ══════════════════════ */

let _contactFilters = { tipo: "", fuente: "", tag_id: "" };

function applyContactFilter(key, value) {
  _contactFilters[key] = value;
  const q = document.getElementById("contact-search")?.value || "";
  const params = new URLSearchParams({ q });
  if (_contactFilters.tipo)   params.set("tipo", _contactFilters.tipo);
  if (_contactFilters.fuente) params.set("fuente", _contactFilters.fuente);
  if (_contactFilters.tag_id) params.set("tag_id", _contactFilters.tag_id);

  fetch(`/api/crm/contacts?${params}`)
    .then(r => r.json())
    .then(data => { _state.contacts = data; renderContactsList(); })
    .catch(console.error);
}

async function triggerCsvImport() {
  const input = document.createElement("input");
  input.type = "file";
  input.accept = ".csv";
  input.onchange = async () => {
    const file = input.files[0];
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    try {
      const r = await fetch("/api/crm/contacts/import-csv", { method: "POST", body: fd });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || "Error");
      showToast(`Importados: ${data.created} contactos${data.skipped ? `, omitidos: ${data.skipped}` : ""}`);
      await loadContacts();
    } catch (err) { showToast("Error al importar: " + err.message, "error"); }
  };
  input.click();
}

/* ════════════════════════ ACTIVITIES ═══════════════════════════ */

async function loadActivities() {
  try {
    _state.activities = await api("GET", "/activities?limit=50");
    const el = document.getElementById("activities-feed");
    if (!_state.activities.length) {
      el.innerHTML = `<div class="empty-state"><p>Sin actividades registradas</p></div>`;
      return;
    }
    el.innerHTML = _state.activities.map(a => renderActivityItem(a, true)).join("");
  } catch (e) { console.error(e); }
}

function renderActivityItem(a, showDelete = true) {
  const icon = TIPO_ICONS[a.tipo] || "📝";
  const meta = [
    a.fecha,
    a.contact_nombre ? `👤 ${esc(a.contact_nombre)}` : "",
    a.property_direccion ? `🏡 ${esc(a.property_direccion)}` : "",
  ].filter(Boolean).join(" · ");
  const del = showDelete
    ? `<button class="activity-del" onclick="deleteActivity(${a.id})">✕</button>`
    : "";
  return `
    <div class="activity-item">
      <div class="activity-icon">${icon}</div>
      <div class="activity-body">
        <div class="activity-desc">${esc(a.descripcion)}</div>
        <div class="activity-meta">${meta}</div>
      </div>
      ${del}
    </div>`;
}

let _actPrefillContactId = null;

function _prefillActivity(contactId) {
  _actPrefillContactId = contactId;
}

async function openActivityModal() {
  try {
    const contacts = await api("GET", "/contacts");
    const sel = document.getElementById("af-contact-id");
    sel.innerHTML = `<option value="">Sin contacto</option>` +
      contacts.map(c => `<option value="${c.id}">${esc(c.nombre)}</option>`).join("");
    if (_actPrefillContactId) {
      sel.value = _actPrefillContactId;
      _actPrefillContactId = null;
    }
  } catch (_) {}
  try {
    const props = await api("GET", "/properties");
    document.getElementById("af-property-id").innerHTML =
      `<option value="">Sin propiedad</option>` +
      props.map(p => `<option value="${p.id}">${esc(p.direccion)} (${esc(p.pueblo)})</option>`).join("");
  } catch (_) {}
  document.getElementById("af-descripcion").value = "";
  document.getElementById("af-tipo").value = "nota";
  document.getElementById("af-fecha").value = new Date().toISOString().slice(0, 10);
  document.getElementById("activity-modal").style.display = "flex";
}

async function submitActivityForm(e) {
  e.preventDefault();
  const body = {
    tipo:        document.getElementById("af-tipo").value,
    descripcion: document.getElementById("af-descripcion").value.trim(),
    fecha:       document.getElementById("af-fecha").value,
    contact_id:  parseInt(document.getElementById("af-contact-id").value) || null,
    property_id: parseInt(document.getElementById("af-property-id").value) || null,
  };
  try {
    await api("POST", "/activities", body);
    closeModal("activity-modal");
    await loadActivities();
    loadDashboard();
    showToast("Actividad registrada");
  } catch (err) { showToast("Error: " + err.message, "error"); }
}

async function deleteActivity(id) {
  if (!confirm("¿Eliminar esta actividad?")) return;
  await api("DELETE", `/activities/${id}`);
  await loadActivities();
}

/* ════════════════════════ CAMPAÑAS ═════════════════════════════ */

async function loadCampaigns() {
  try {
    const data = await apiRaw("GET", "/api/crm/campaigns");
    renderCampaignsList(data.items);
  } catch (e) { console.error(e); }
}

function renderCampaignsList(items) {
  const el = document.getElementById("campaigns-list");
  if (!items.length) {
    el.innerHTML = `<div class="empty-state"><p>Sin campañas aún</p><small>Crea tu primera campaña de email masivo</small></div>`;
    return;
  }
  el.innerHTML = `
    <div class="campaigns-table">
      <div class="camp-table-header">
        <span>Nombre</span>
        <span>Segmento</span>
        <span>Estado</span>
        <span>Enviados</span>
        <span>Acciones</span>
      </div>
      ${items.map(c => {
        const s = STATUS_LABELS[c.status] || { label: c.status, cls: "" };
        return `<div class="camp-table-row">
          <span class="camp-nombre">${esc(c.nombre)}</span>
          <span class="camp-segmento">${esc(c.segmento)}</span>
          <span><span class="camp-status ${s.cls}">${s.label}</span></span>
          <span>${c.total_enviados} / ${c.total_enviados + c.total_fallidos}</span>
          <span class="camp-actions">
            <button class="btn-secondary btn-sm" onclick="openCampaignDetail(${c.id})">Ver</button>
            ${c.status === "borrador" || c.status === "error"
              ? `<button class="btn-primary btn-sm" onclick="triggerSend(${c.id})">Enviar</button>`
              : ""}
            ${c.status === "borrador"
              ? `<button class="btn-danger btn-sm" onclick="deleteCampaign(${c.id})">Eliminar</button>`
              : ""}
          </span>
        </div>`;
      }).join("")}
    </div>`;
}

async function openCampaignModal() {
  _editCampaignId = null;
  document.getElementById("campaign-modal-title").textContent = "Nueva Campaña de Email";
  document.getElementById("campaign-form").reset();

  // Load templates
  try {
    const data = await apiRaw("GET", "/api/crm/campaigns/templates");
    document.getElementById("template-buttons").innerHTML = data.templates.map(t =>
      `<button type="button" class="tpl-btn" onclick="loadTemplate('${t.id}')">${t.nombre}</button>`
    ).join("");
  } catch (_) {}

  document.getElementById("campaign-modal").style.display = "flex";
}

async function loadTemplate(tplId) {
  try {
    const t = await apiRaw("GET", `/api/crm/campaigns/templates/${tplId}`);
    document.getElementById("cam-asunto").value    = t.asunto;
    document.getElementById("cam-html-body").value = t.html_body.trim();
    showToast("Plantilla cargada", "info");
  } catch (e) { showToast("Error al cargar plantilla", "error"); }
}

async function submitCampaignForm(e) {
  e.preventDefault();
  const body = {
    nombre:    document.getElementById("cam-nombre").value.trim(),
    asunto:    document.getElementById("cam-asunto").value.trim(),
    html_body: document.getElementById("cam-html-body").value.trim(),
    segmento:  document.getElementById("cam-segmento").value,
  };
  try {
    await apiRaw("POST", "/api/crm/campaigns", body);
    showToast("Campaña guardada como borrador");
    closeModal("campaign-modal");
    await loadCampaigns();
  } catch (err) { showToast("Error: " + err.message, "error"); }
}

async function openCampaignDetail(id) {
  try {
    const c = await apiRaw("GET", `/api/crm/campaigns/${id}`);
    renderCampaignDetail(c);
    document.getElementById("campaign-detail-modal").style.display = "flex";
    if (c.status === "enviando") startCampaignPoll(id);
  } catch (e) { showToast("Error al cargar campaña", "error"); }
}

function renderCampaignDetail(c) {
  document.getElementById("cdm-title").textContent = c.nombre;
  const s = STATUS_LABELS[c.status] || { label: c.status, cls: "" };
  const total = c.sends.length;
  const enviados = c.sends.filter(s => s.status === "enviado").length;
  const fallidos = c.sends.filter(s => s.status === "fallido").length;
  const pct = total > 0 ? Math.round((enviados / total) * 100) : 0;

  document.getElementById("campaign-detail-body").innerHTML = `
    <div style="margin-bottom:20px;">
      <div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:12px;">
        <span class="camp-status ${s.cls}">${s.label}</span>
        <span style="font-size:13px;color:var(--text-muted);">Segmento: <strong>${c.segmento}</strong></span>
        <span style="font-size:13px;color:var(--text-muted);">Asunto: <strong>${esc(c.asunto)}</strong></span>
      </div>
      ${total > 0 ? `
      <div class="camp-progress-container">
        <div class="camp-progress-bar" id="cdm-progress-bar" style="width:${pct}%"></div>
      </div>
      <div style="display:flex;justify-content:space-between;font-size:12px;color:var(--text-muted);margin-top:6px;">
        <span id="cdm-progress-text">Enviados: ${enviados} / ${total} (${pct}%)</span>
        <span style="color:var(--danger);">Fallidos: ${fallidos}</span>
      </div>` : ""}
    </div>
    ${c.sends.length > 0 ? `
    <div style="max-height:300px;overflow-y:auto;">
      <table class="sends-table">
        <thead><tr><th>Email</th><th>Estado</th><th>Hora</th></tr></thead>
        <tbody>
          ${c.sends.map(s => `
            <tr>
              <td>${esc(s.email)}</td>
              <td><span class="send-status send-${s.status}">${s.status}</span></td>
              <td style="font-size:11px;color:var(--text-muted);">${s.sent_at ? new Date(s.sent_at).toLocaleTimeString("es-PR") : "—"}</td>
            </tr>`).join("")}
        </tbody>
      </table>
    </div>` : `<div class="empty-state"><p>Sin destinatarios aún</p></div>`}
  `;
}

async function triggerSend(id) {
  if (!confirm("¿Enviar esta campaña ahora? Se enviará a todos los contactos del segmento seleccionado.")) return;
  try {
    const r = await apiRaw("POST", `/api/crm/campaigns/${id}/send`);
    showToast(`Enviando a ${r.total_recipients} contactos…`, "info");
    await loadCampaigns();
    await openCampaignDetail(id);
  } catch (err) { showToast("Error: " + err.message, "error"); }
}

function startCampaignPoll(id) {
  if (_campaignPollTimer) clearInterval(_campaignPollTimer);
  _campaignPollTimer = setInterval(async () => {
    try {
      const s = await apiRaw("GET", `/api/crm/campaigns/${id}/status`);
      const pct = s.total > 0 ? Math.round((s.enviados / s.total) * 100) : 0;
      const bar = document.getElementById("cdm-progress-bar");
      const txt = document.getElementById("cdm-progress-text");
      if (bar) bar.style.width = pct + "%";
      if (txt) txt.textContent = `Enviados: ${s.enviados} / ${s.total} (${pct}%)`;
      if (s.status !== "enviando") {
        clearInterval(_campaignPollTimer);
        _campaignPollTimer = null;
        showToast(s.status === "completado"
          ? `Campaña completada: ${s.enviados} enviados, ${s.fallidos} fallidos`
          : "Error al enviar campaña", s.status === "completado" ? "success" : "error");
        await loadCampaigns();
      }
    } catch (_) {}
  }, 2000);
}

async function deleteCampaign(id) {
  if (!confirm("¿Eliminar esta campaña?")) return;
  try {
    await apiRaw("DELETE", `/api/crm/campaigns/${id}`);
    showToast("Campaña eliminada", "info");
    await loadCampaigns();
  } catch (err) { showToast("Error: " + err.message, "error"); }
}

/* ════════════════════════ ANALÍTICAS ════════════════════════════ */

async function loadAnalytics() {
  try {
    const [summary, monthly, revenue, sources, opoSummary] = await Promise.all([
      apiRaw("GET", "/api/crm/analytics/summary"),
      apiRaw("GET", "/api/crm/analytics/pipeline-monthly"),
      apiRaw("GET", "/api/crm/analytics/revenue-monthly"),
      apiRaw("GET", "/api/crm/analytics/contact-sources"),
      apiRaw("GET", "/api/crm/analytics/oportunidades-summary"),
    ]);

    // KPIs
    document.getElementById("analytics-kpis").innerHTML = `
      <div class="stat-card">
        <div class="stat-label">Contactos</div>
        <div class="stat-value">${summary.total_contacts}</div>
        <div class="stat-sub">total en CRM</div>
      </div>
      <div class="stat-card accent">
        <div class="stat-label">Oportunidades</div>
        <div class="stat-value">${summary.total_oportunidades}</div>
        <div class="stat-sub">$${fmtMoney(summary.pipeline_opo_value)} en pipeline</div>
      </div>
      <div class="stat-card success">
        <div class="stat-label">Revenue Cerrado</div>
        <div class="stat-value small">$${fmtMoney(summary.closed_value)}</div>
        <div class="stat-sub">propiedades cerradas</div>
      </div>
      <div class="stat-card warning">
        <div class="stat-label">Oportunidades Ganadas</div>
        <div class="stat-value small">$${fmtMoney(summary.won_value)}</div>
        <div class="stat-sub">total ganado</div>
      </div>
    `;

    renderPipelineChart(monthly.data);
    renderRevenueChart(revenue.data);
    renderSourcesChart(sources.data);
    renderOpoPipelineChart(opoSummary.data);
  } catch (e) { console.error(e); }
}

function renderPipelineChart(data) {
  if (_charts.pipeline) { _charts.pipeline.destroy(); delete _charts.pipeline; }
  if (!data.length) return;

  const months   = [...new Set(data.map(d => d.month))].sort();
  const stages   = [...new Set(data.map(d => d.stage))];
  const colors   = { prospecto:"#1565c0", activo:"#2e7d32", oferta:"#f57f17", contrato:"#ad1457", cerrado:"#1b5e20" };

  const datasets = stages.map(stage => ({
    label: STAGE_LABELS[stage] || stage,
    data: months.map(m => {
      const row = data.find(d => d.month === m && d.stage === stage);
      return row ? row.count : 0;
    }),
    backgroundColor: (colors[stage] || "#999") + "CC",
  }));

  const ctx = document.getElementById("chart-pipeline").getContext("2d");
  _charts.pipeline = new Chart(ctx, {
    type: "bar",
    data: { labels: months, datasets },
    options: { responsive: true, plugins: { legend: { position: "bottom" } },
               scales: { x: { stacked: true }, y: { stacked: true } } },
  });
}

function renderRevenueChart(data) {
  if (_charts.revenue) { _charts.revenue.destroy(); delete _charts.revenue; }
  const ctx = document.getElementById("chart-revenue").getContext("2d");
  _charts.revenue = new Chart(ctx, {
    type: "line",
    data: {
      labels: data.map(d => d.month),
      datasets: [{
        label: "Ingresos Cerrados ($)",
        data: data.map(d => d.total),
        borderColor: "#1a6b8a",
        backgroundColor: "rgba(26,107,138,0.12)",
        fill: true,
        tension: 0.3,
      }],
    },
    options: { responsive: true, plugins: { legend: { display: false } } },
  });
}

function renderSourcesChart(data) {
  if (_charts.sources) { _charts.sources.destroy(); delete _charts.sources; }
  const FUENTE_COLORS = {
    manual:    "#1a6b8a",
    instagram: "#c13584",
    facebook:  "#3b5998",
    email:     "#f4a623",
  };
  const ctx = document.getElementById("chart-sources").getContext("2d");
  _charts.sources = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: data.map(d => d.fuente),
      datasets: [{
        data: data.map(d => d.count),
        backgroundColor: data.map(d => FUENTE_COLORS[d.fuente] || "#999"),
      }],
    },
    options: { responsive: true, plugins: { legend: { position: "bottom" } } },
  });
}

function renderOpoPipelineChart(data) {
  if (_charts.opo) { _charts.opo.destroy(); delete _charts.opo; }
  const filtered = data.filter(d => d.total_valor > 0);
  const ctx = document.getElementById("chart-oportunidades").getContext("2d");
  _charts.opo = new Chart(ctx, {
    type: "bar",
    data: {
      labels: filtered.map(d => OPO_ETAPA_LABELS[d.etapa] || d.etapa),
      datasets: [{
        label: "Valor ($)",
        data: filtered.map(d => d.total_valor),
        backgroundColor: filtered.map(d =>
          d.etapa === "cerrado_ganado" ? "rgba(40,167,69,0.8)" :
          d.etapa === "cerrado_perdido" ? "rgba(220,53,69,0.8)" :
          "rgba(26,107,138,0.7)"
        ),
      }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: { y: { ticks: { callback: v => "$" + fmtMoney(v) } } },
    },
  });
}

/* ════════════════════════ INTEGRACIONES ════════════════════════ */

async function loadIntegrations() {
  const el = document.getElementById("integrations-content");

  let metaConfig = null;
  try {
    metaConfig = await apiRaw("GET", "/api/webhooks/meta/config");
  } catch (_) {}

  const webhookUrl = window.location.origin + "/api/webhooks/meta";

  el.innerHTML = `
    <!-- SMTP Card -->
    <div class="int-card">
      <div class="int-card-header">
        <div class="int-icon">✉️</div>
        <div>
          <div class="int-title">Email / Gmail SMTP</div>
          <div class="int-subtitle">Para enviar campañas de email masivo</div>
        </div>
      </div>
      <div class="int-steps">
        <div class="int-step"><span class="step-num">1</span> Activa la verificación en 2 pasos en tu cuenta de Google</div>
        <div class="int-step"><span class="step-num">2</span> Ve a <strong>myaccount.google.com/apppasswords</strong> y genera una App Password</div>
        <div class="int-step"><span class="step-num">3</span> Agrega al archivo <code>.env</code>:<br>
          <code class="env-block">SMTP_USER=tu@gmail.com<br>SMTP_PASSWORD=xxxx xxxx xxxx xxxx<br>SMTP_FROM_NAME=Tu Nombre</code>
        </div>
        <div class="int-step"><span class="step-num">4</span> Reinicia el servidor</div>
      </div>
    </div>

    <!-- Meta Card -->
    <div class="int-card">
      <div class="int-card-header">
        <div class="int-icon">📱</div>
        <div>
          <div class="int-title">Instagram & Facebook DMs</div>
          <div class="int-subtitle">Captura clientes que te escriben por DM</div>
        </div>
        <div style="margin-left:auto;">
          <span class="int-status ${metaConfig?.page_access_token_configured ? 'int-ok' : 'int-warn'}">
            ${metaConfig?.page_access_token_configured ? '● Conectado' : '● No configurado'}
          </span>
        </div>
      </div>
      <div class="int-steps">
        <div class="int-step"><span class="step-num">1</span> Ve a <strong>developers.facebook.com</strong> → Crear app → Tipo: Business</div>
        <div class="int-step"><span class="step-num">2</span> Agrega los productos: <strong>Messenger</strong> e <strong>Instagram</strong></div>
        <div class="int-step"><span class="step-num">3</span> En Webhooks, configura la URL:
          <div class="webhook-url-row">
            <code id="webhook-url-display">${webhookUrl}</code>
            <button class="btn-secondary btn-sm" onclick="copyWebhookUrl()">Copiar</button>
          </div>
        </div>
        <div class="int-step"><span class="step-num">4</span> Token de verificación:
          <code class="env-block">${metaConfig?.verify_token || "listapro_verify_2024"}</code>
        </div>
        <div class="int-step"><span class="step-num">5</span> Suscríbete al evento <strong>messages</strong> en ambas plataformas</div>
        <div class="int-step"><span class="step-num">6</span> Obtén el Page Access Token desde Graph API Explorer y agrega al <code>.env</code>:
          <code class="env-block">META_PAGE_ACCESS_TOKEN=EAAxxxxx...<br>META_VERIFY_TOKEN=listapro_verify_2024</code>
        </div>
        <div class="int-step"><span class="step-num">7</span> Para pruebas locales, usa <strong>ngrok</strong>:<br>
          <code class="env-block">ngrok http 8003</code>
          y usa la URL HTTPS que te da ngrok como webhook URL
        </div>
      </div>
    </div>
  `;
}

function copyWebhookUrl() {
  const url = document.getElementById("webhook-url-display")?.textContent;
  if (url) {
    navigator.clipboard.writeText(url).then(() => showToast("URL copiada", "info"));
  }
}

/* ── Modals ─────────────────────────────────────────────────────── */

function closeModal(id) {
  document.getElementById(id).style.display = "none";
  if (id === "campaign-detail-modal" && _campaignPollTimer) {
    clearInterval(_campaignPollTimer);
    _campaignPollTimer = null;
  }
}

document.addEventListener("click", e => {
  if (e.target.classList.contains("modal-overlay")) {
    const id = e.target.id;
    closeModal(id);
  }
});

/* ── Formatters ─────────────────────────────────────────────────── */

function esc(str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function fmtMoney(n) {
  return Number(n || 0).toLocaleString("en-US");
}

function fmtNum(n) {
  return Number(n || 0).toLocaleString("en-US");
}

function daysDiff(dateStr) {
  if (!dateStr) return 999;
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const d = new Date(dateStr + "T00:00:00");
  return Math.round((d - today) / 86400000);
}
