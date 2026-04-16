/* ─── Municipios de Puerto Rico (78) ──────────────────────────── */
const MUNICIPIOS = [
  "Adjuntas","Aguada","Aguadilla","Aguas Buenas","Aibonito","Añasco","Arecibo",
  "Arroyo","Barceloneta","Barranquitas","Bayamón","Cabo Rojo","Caguas","Camuy",
  "Canóvanas","Carolina","Cataño","Cayey","Ceiba","Ciales","Cidra","Coamo",
  "Comerío","Corozal","Culebra","Dorado","Fajardo","Florida","Guánica","Guayama",
  "Guayanilla","Guaynabo","Gurabo","Hatillo","Hormigueros","Humacao","Isabela",
  "Jayuya","Juana Díaz","Juncos","Lajas","Lares","Las Marías","Las Piedras",
  "Loíza","Luquillo","Manatí","Maricao","Maunabo","Mayagüez","Moca","Morovis",
  "Naguabo","Naranjito","Orocovis","Patillas","Peñuelas","Ponce","Quebradillas",
  "Rincón","Río Grande","Sabana Grande","Salinas","San Germán","San Juan",
  "San Lorenzo","San Sebastián","Santa Isabel","Toa Alta","Toa Baja","Trujillo Alto",
  "Utuado","Vega Alta","Vega Baja","Vieques","Villalba","Yabucoa","Yauco"
];

/* ─── Populate pueblo select ──────────────────────────────────── */
document.addEventListener("DOMContentLoaded", () => {
  const select = document.getElementById("pueblo");
  MUNICIPIOS.forEach(m => {
    const opt = document.createElement("option");
    opt.value = m;
    opt.textContent = m;
    select.appendChild(opt);
  });
});

/* ─── Photo Preview ───────────────────────────────────────────── */
function setupPhotoPreview(inputId, previewId, isPortada = false) {
  const input = document.getElementById(inputId);
  const preview = document.getElementById(previewId);

  input.addEventListener("change", () => {
    preview.innerHTML = "";
    Array.from(input.files).forEach((file, i) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const img = document.createElement("img");
        img.src = e.target.result;
        img.className = "photo-thumb" + (isPortada && i === 0 ? " portada" : "");
        img.title = file.name;
        preview.appendChild(img);
      };
      reader.readAsDataURL(file);
    });
  });
}

setupPhotoPreview("foto_portada", "portada-preview", true);
setupPhotoPreview("fotos_extras", "extras-preview", false);
setupPhotoPreview("logo_agencia", "logo-agencia-preview", false);

/* ─── Color picker hex labels ─────────────────────────────────── */
document.addEventListener("DOMContentLoaded", () => {
  ["color_primario", "color_acento"].forEach(id => {
    const input = document.getElementById(id);
    const label = document.getElementById(id.replace("_", "-") + "-hex");
    if (!input || !label) return;
    input.addEventListener("input", () => { label.textContent = input.value; });
  });
});

/* ─── Form Submission ─────────────────────────────────────────── */
const form = document.getElementById("property-form");
const submitBtn = document.getElementById("submit-btn");
const btnText = document.getElementById("btn-text");
const btnIcon = document.getElementById("btn-icon");
const loadingOverlay = document.getElementById("loading-overlay");
const formSection = document.getElementById("form-section");
const resultsSection = document.getElementById("results-section");
const formError = document.getElementById("form-error");
const errorText = document.getElementById("error-text");

function showError(msg) {
  errorText.textContent = msg;
  formError.style.display = "block";
  formError.scrollIntoView({ behavior: "smooth", block: "center" });
}

function hideError() {
  formError.style.display = "none";
}

function setLoading(on) {
  if (on) {
    submitBtn.disabled = true;
    btnText.textContent = "Generando…";
    btnIcon.textContent = "⏳";
    loadingOverlay.style.display = "flex";
  } else {
    submitBtn.disabled = false;
    btnText.textContent = "Generar Descripción con IA";
    btnIcon.textContent = "✨";
    loadingOverlay.style.display = "none";
  }
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  hideError();

  // Basic client-side validation
  const foto = document.getElementById("foto_portada").files[0];
  if (!foto) {
    showError("Por favor sube al menos una foto de portada.");
    return;
  }

  const formData = new FormData(form);

  // Collect checked amenidades into individual form entries
  // (checkboxes with same name are already handled by FormData natively)

  setLoading(true);

  try {
    const response = await fetch("/api/generate", {
      method: "POST",
      body: formData,
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Error desconocido del servidor.");
    }

    // Render results
    document.getElementById("listing-description-text").textContent = data.listing_description;
    document.getElementById("instagram-copy-text").textContent = data.instagram_copy;

    const coverImg = document.getElementById("result-cover-photo");
    if (data.foto_portada_url) {
      coverImg.src = data.foto_portada_url;
      coverImg.style.display = "block";
    } else {
      coverImg.style.display = "none";
    }

    const pdfBtn = document.getElementById("download-pdf-btn");
    if (data.pdf_url) {
      pdfBtn.href = data.pdf_url;
      pdfBtn.download = "listado-listapro.pdf";
      pdfBtn.style.display = "flex";
    } else {
      pdfBtn.style.display = "none";
    }

    // Instagram carousel
    const igBtn = document.getElementById("download-ig-btn");
    const publishBtn = document.getElementById("publish-ig-btn");
    if (data.carousel_urls && data.carousel_urls.length > 0) {
      _setupCarousel(data.carousel_urls);
      igBtn.href = data.carousel_urls[0];
      igBtn.download = "instagram-slide-1.jpg";
      igBtn.style.display = "flex";
      publishBtn.style.display = "inline-flex";
      publishBtn.dataset.imageUrl = data.carousel_urls[0];
    } else if (data.instagram_image_url) {
      igBtn.href = data.instagram_image_url;
      igBtn.download = "instagram-listapro.jpg";
      igBtn.style.display = "flex";
      publishBtn.style.display = "inline-flex";
      publishBtn.dataset.imageUrl = data.instagram_image_url;
    } else {
      igBtn.style.display = "none";
      publishBtn.style.display = "none";
    }

    // Store data for video generation
    window._lastPortadaUrl = data.foto_portada_url || "";
    window._lastExtrasUrls = data.fotos_extras_urls || [];
    window._lastAgenciaLogoUrl = data.agencia_logo_url || "";
    window._lastPropertyData = {
      tipo_propiedad: form.tipo_propiedad.value,
      operacion: form.operacion.value,
      direccion: form.direccion.value,
      pueblo: form.pueblo.value,
      precio: form.precio.value,
      habitaciones: form.habitaciones.value,
      banos: form.banos.value,
      pies_cuadrados_construccion: form.pies_cuadrados_construccion.value,
      estacionamientos: form.estacionamientos.value,
      nombre_agente: form.nombre_agente.value,
      licencia_agente: form.licencia_agente.value,
      telefono_agente: form.telefono_agente.value,
      nombre_agencia: form.nombre_agencia?.value || "",
      tagline_agencia: form.tagline_agencia?.value || "",
      color_primario: document.getElementById("color_primario")?.value || "#1a6b8a",
      color_acento: document.getElementById("color_acento")?.value || "#f4a623",
    };

    // Show tema selector, video button, and CRM save button
    window._lastTema = 0;
    document.getElementById("tema-selector").style.display = "block";
    document.getElementById("generate-video-btn").style.display = "flex";
    document.getElementById("save-crm-btn").style.display = "flex";
    document.getElementById("video-section").style.display = "none";

    // Switch views
    formSection.style.display = "none";
    resultsSection.style.display = "block";
    window.scrollTo({ top: 0, behavior: "smooth" });

  } catch (err) {
    showError(err.message || "Hubo un error al conectar con el servidor. Verifica tu conexión.");
  } finally {
    setLoading(false);
  }
});

/* ─── Copy to Clipboard ───────────────────────────────────────── */
document.querySelectorAll(".copy-btn").forEach(btn => {
  btn.addEventListener("click", async () => {
    const targetId = btn.dataset.target;
    const text = document.getElementById(targetId)?.textContent || "";

    try {
      await navigator.clipboard.writeText(text);
      const original = btn.textContent;
      btn.textContent = "¡Copiado!";
      btn.classList.add("copied");
      setTimeout(() => {
        btn.textContent = original;
        btn.classList.remove("copied");
      }, 2000);
    } catch {
      // Fallback for older browsers
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      btn.textContent = "¡Copiado!";
      btn.classList.add("copied");
      setTimeout(() => {
        btn.textContent = "Copiar";
        btn.classList.remove("copied");
      }, 2000);
    }
  });
});

/* ─── Tema pill selection ─────────────────────────────────────── */
document.querySelectorAll(".tema-pill").forEach(pill => {
  pill.addEventListener("click", () => {
    document.querySelectorAll(".tema-pill").forEach(p => p.classList.remove("active"));
    pill.classList.add("active");
    window._lastTema = parseInt(pill.dataset.tema ?? "0", 10);
  });
});

/* ─── Publish to Instagram ────────────────────────────────────── */
document.getElementById("publish-ig-btn").addEventListener("click", async function () {
  const btn = this;
  const statusDiv = document.getElementById("publish-status");
  const imageUrl = btn.dataset.imageUrl;
  const caption = document.getElementById("instagram-copy-text").textContent;

  btn.disabled = true;
  statusDiv.style.display = "block";
  statusDiv.className = "publish-status loading";
  statusDiv.textContent = "⏳ Publicando en Instagram…";

  try {
    const res = await fetch("/api/publish/instagram", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image_url: imageUrl, caption }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Error al publicar.");
    statusDiv.className = "publish-status success";
    statusDiv.textContent = "✅ Publicado en Instagram exitosamente.";
  } catch (err) {
    statusDiv.className = "publish-status error";
    statusDiv.textContent = "⚠️ " + (err.message || "No se pudo publicar.");
    btn.disabled = false;
  }
});

/* ─── Generate Video Reel ─────────────────────────────────────── */
const VIDEO_STATUS_LABELS = {
  pending:     "En cola",
  preparing:   "Preparando fotos",
  installing:  "Instalando dependencias",
  bundling:    "Compilando proyecto",
  composing:   "Configurando composición",
  rendering:   "Renderizando frames",
  finalizing:  "Finalizando",
  done:        "¡Listo!",
  error:       "Error",
};

let _videoPollTimer = null;

document.getElementById("generate-video-btn").addEventListener("click", async function () {
  const btn = this;
  btn.disabled = true;
  btn.textContent = "⏳ Iniciando…";

  const videoSection = document.getElementById("video-section");
  const progressFill = document.getElementById("video-progress-fill");
  const progressPct = document.getElementById("video-progress-pct");
  const statusLabel = document.getElementById("video-status-label");
  const statusMsg = document.getElementById("video-status-msg");
  const dlBtn = document.getElementById("download-video-btn");

  videoSection.style.display = "block";
  dlBtn.style.display = "none";
  progressFill.style.width = "0%";
  progressPct.textContent = "0%";
  statusLabel.textContent = "En cola";
  statusMsg.textContent = "Iniciando renderizado…";
  videoSection.scrollIntoView({ behavior: "smooth", block: "start" });

  try {
    const res = await fetch("/api/video/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        portada_url: window._lastPortadaUrl,
        extras_urls: window._lastExtrasUrls,
        data: {
          ...window._lastPropertyData,
          logo_agencia_local: window._lastAgenciaLogoUrl
            ? window._lastAgenciaLogoUrl.replace(/^\//, "")
            : null,
          tema: window._lastTema ?? 0,
        },
      }),
    });
    const { job_id } = await res.json();
    if (!job_id) throw new Error("No se recibió job_id del servidor.");

    // Poll for progress
    if (_videoPollTimer) clearInterval(_videoPollTimer);
    _videoPollTimer = setInterval(async () => {
      try {
        const sr = await fetch(`/api/video/status/${job_id}`);
        const job = await sr.json();
        const pct = job.progress || 0;
        progressFill.style.width = pct + "%";
        progressPct.textContent = pct + "%";
        statusLabel.textContent = VIDEO_STATUS_LABELS[job.status] || job.status;
        statusMsg.textContent = _videoStatusMessage(job.status);

        if (job.status === "done") {
          clearInterval(_videoPollTimer);
          progressFill.style.width = "100%";
          progressPct.textContent = "100%";
          dlBtn.href = job.video_url;
          dlBtn.download = "reel-listapro.mp4";
          dlBtn.style.display = "flex";
          btn.textContent = "✅ Video Generado";
        } else if (job.status === "error") {
          clearInterval(_videoPollTimer);
          statusMsg.textContent = "⚠️ Error: " + (job.error || "Fallo al renderizar.");
          statusLabel.textContent = "Error";
          btn.disabled = false;
          btn.textContent = "🔄 Reintentar";
        }
      } catch (_) { /* network hiccup, keep polling */ }
    }, 2000);

  } catch (err) {
    statusMsg.textContent = "⚠️ " + (err.message || "Error al iniciar el video.");
    statusLabel.textContent = "Error";
    btn.disabled = false;
    btn.textContent = "🎬 Generar Video Reel";
  }
});

function _videoStatusMessage(status) {
  const msgs = {
    pending:     "En la cola de renderizado…",
    preparing:   "Copiando fotos al proyecto…",
    installing:  "Instalando dependencias npm (solo la primera vez)…",
    bundling:    "Compilando con webpack, un momento…",
    composing:   "Configurando la composición del video…",
    rendering:   "Renderizando frames con Remotion…",
    finalizing:  "Guardando el archivo de video…",
    done:        "¡Video listo para descargar!",
    error:       "Ocurrió un error durante el renderizado.",
  };
  return msgs[status] || "Procesando…";
}

/* ─── Instagram Carousel ─────────────────────────────────────── */
let _carouselSlides = [];
let _carouselIdx = 0;

function _setupCarousel(urls) {
  _carouselSlides = urls;
  _carouselIdx = 0;
  const section = document.getElementById("carousel-section");
  if (!section) return;
  section.style.display = "";
  const badge = document.getElementById("carousel-slide-count");
  if (badge) badge.textContent = urls.length + " slides";
  const thumbs = document.getElementById("carousel-thumbs");
  thumbs.innerHTML = "";
  urls.forEach((url, i) => {
    const img = document.createElement("img");
    img.src = url;
    img.className = "carousel-thumb" + (i === 0 ? " active" : "");
    img.addEventListener("click", () => { _carouselIdx = i; _renderCarousel(); });
    thumbs.appendChild(img);
  });
  _renderCarousel();
}

function _renderCarousel() {
  const url = _carouselSlides[_carouselIdx];
  document.getElementById("carousel-img").src = url;
  document.getElementById("carousel-current").textContent = _carouselIdx + 1;
  document.getElementById("carousel-total").textContent = _carouselSlides.length;
  const dl = document.getElementById("carousel-dl-current");
  dl.href = url;
  dl.download = `slide_${_carouselIdx + 1}.jpg`;
  document.querySelectorAll(".carousel-thumb").forEach((el, i) => {
    el.classList.toggle("active", i === _carouselIdx);
  });
}

function carouselNav(dir) {
  const n = _carouselSlides.length;
  if (!n) return;
  _carouselIdx = (_carouselIdx + dir + n) % n;
  _renderCarousel();
}

async function carouselDownloadAll() {
  for (let i = 0; i < _carouselSlides.length; i++) {
    const a = document.createElement("a");
    a.href = _carouselSlides[i];
    a.download = `slide_${i + 1}.jpg`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    await new Promise(r => setTimeout(r, 400));
  }
}

/* ─── Save to CRM ─────────────────────────────────────────────── */
document.getElementById("save-crm-btn").addEventListener("click", async () => {
  // Populate contact dropdown
  const sel = document.getElementById("crm-contact-select");
  sel.innerHTML = '<option value="">Sin contacto (guardar sin asignar)</option>';
  try {
    const res = await fetch("/api/crm/contacts");
    if (res.ok) {
      const contacts = await res.json();
      contacts.forEach(c => {
        const opt = document.createElement("option");
        opt.value = c.id;
        opt.textContent = c.nombre + (c.telefono ? ` — ${c.telefono}` : "");
        sel.appendChild(opt);
      });
    }
  } catch (_) {}

  const modal = document.getElementById("crm-save-modal");
  modal.style.display = "flex";
  document.getElementById("crm-save-status").style.display = "none";
  document.getElementById("crm-notes").value = "";
});

async function saveToCRM() {
  const pd = window._lastPropertyData || {};
  const statusDiv = document.getElementById("crm-save-status");
  statusDiv.style.display = "none";

  const payload = {
    contact_id: document.getElementById("crm-contact-select").value || null,
    stage: document.getElementById("crm-stage-select").value,
    notas_crm: document.getElementById("crm-notes").value,
    tipo_propiedad: pd.tipo_propiedad || "",
    operacion: pd.operacion || "",
    direccion: pd.direccion || "",
    pueblo: pd.pueblo || "",
    precio: pd.precio ? parseFloat(pd.precio) : null,
    habitaciones: pd.habitaciones ? parseInt(pd.habitaciones) : null,
    banos: pd.banos ? parseFloat(pd.banos) : null,
    pies_cuadrados_construccion: pd.pies_cuadrados_construccion ? parseFloat(pd.pies_cuadrados_construccion) : null,
    estacionamientos: pd.estacionamientos ? parseInt(pd.estacionamientos) : null,
    nombre_agente: pd.nombre_agente || "",
    telefono_agente: pd.telefono_agente || "",
    nombre_agencia: pd.nombre_agencia || "",
    listing_description: document.getElementById("listing-description-text")?.textContent || "",
    instagram_copy: document.getElementById("instagram-copy-text")?.textContent || "",
    foto_portada_url: window._lastPortadaUrl || "",
    fotos_extras_urls: JSON.stringify(window._lastExtrasUrls || []),
  };

  try {
    const res = await fetch("/api/crm/properties", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Error al guardar.");
    statusDiv.className = "";
    statusDiv.style.cssText = "display:block;margin-bottom:14px;padding:10px 14px;border-radius:7px;font-size:13px;font-weight:600;background:#d4edda;color:#155724;";
    statusDiv.textContent = "✅ Guardado en CRM exitosamente.";
    setTimeout(() => {
      document.getElementById("crm-save-modal").style.display = "none";
    }, 1400);
  } catch (err) {
    statusDiv.style.cssText = "display:block;margin-bottom:14px;padding:10px 14px;border-radius:7px;font-size:13px;font-weight:600;background:#f8d7da;color:#721c24;";
    statusDiv.textContent = "⚠️ " + (err.message || "No se pudo guardar.");
  }
}

/* ─── New Listing Reset ───────────────────────────────────────── */
document.getElementById("new-listing-btn").addEventListener("click", () => {
  form.reset();
  document.getElementById("portada-preview").innerHTML = "";
  document.getElementById("extras-preview").innerHTML = "";
  document.getElementById("download-pdf-btn").style.display = "none";
  document.getElementById("download-ig-btn").style.display = "none";
  document.getElementById("carousel-section").style.display = "none";
  document.getElementById("publish-ig-btn").style.display = "none";
  _carouselSlides = []; _carouselIdx = 0;
  document.getElementById("publish-status").style.display = "none";
  document.getElementById("generate-video-btn").style.display = "none";
  document.getElementById("save-crm-btn").style.display = "none";
  document.getElementById("crm-save-modal").style.display = "none";
  document.getElementById("video-section").style.display = "none";
  if (_videoPollTimer) { clearInterval(_videoPollTimer); _videoPollTimer = null; }
  const videoBtn = document.getElementById("generate-video-btn");
  videoBtn.disabled = false;
  videoBtn.textContent = "🎬 Generar Video Reel";
  window._lastPortadaUrl = null;
  window._lastExtrasUrls = [];
  window._lastPropertyData = {};
  hideError();

  resultsSection.style.display = "none";
  formSection.style.display = "block";
  window.scrollTo({ top: 0, behavior: "smooth" });
});
