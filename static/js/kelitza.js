/* ============================================
   KELITZA MÉNDEZ — Website JavaScript
   Mendez Group | Puerto Rico
   ============================================ */

'use strict';

// ── 1. AOS Init ──────────────────────────────────────────────────────────────
AOS.init({
  duration: 750,
  easing: 'ease-out-cubic',
  once: true,
  offset: 60,
});

// ── 2. Scroll Progress Bar ────────────────────────────────────────────────────
const progressBar = document.getElementById('scroll-progress');
function updateScrollProgress() {
  const scrollTop = window.scrollY;
  const docHeight = document.documentElement.scrollHeight - window.innerHeight;
  const pct       = docHeight > 0 ? (scrollTop / docHeight) * 100 : 0;
  progressBar.style.width = pct + '%';
}
window.addEventListener('scroll', updateScrollProgress, { passive: true });

// ── 3. Navbar Scroll Effect ───────────────────────────────────────────────────
const navbar   = document.getElementById('navbar');
const sentinel = document.getElementById('nav-sentinel');
new IntersectionObserver(
  ([e]) => navbar.classList.toggle('scrolled', !e.isIntersecting),
  { threshold: 0 }
).observe(sentinel);

const hamburger = document.getElementById('hamburger');
const navLinks  = document.getElementById('navLinks');
hamburger.addEventListener('click', () => {
  hamburger.classList.toggle('open');
  navLinks.classList.toggle('open');
});
navLinks.querySelectorAll('a').forEach(l => {
  l.addEventListener('click', () => {
    hamburger.classList.remove('open');
    navLinks.classList.remove('open');
  });
});

// ── 4. Hero Parallax ─────────────────────────────────────────────────────────
const heroBg = document.getElementById('heroBg');
function handleParallax() {
  const offset = Math.min(window.scrollY * 0.35, window.innerHeight * 0.3);
  heroBg.style.transform = `translateY(${offset}px) scale(1.12)`;
}
window.addEventListener('scroll', handleParallax, { passive: true });

// ── 5. Counter Animation ──────────────────────────────────────────────────────
function animateCounter(el, target, duration = 1800) {
  const start  = performance.now();
  const update = (time) => {
    const progress = Math.min((time - start) / duration, 1);
    const ease     = 1 - Math.pow(1 - progress, 3);
    el.textContent = Math.round(target * ease).toLocaleString();
    if (progress < 1) requestAnimationFrame(update);
  };
  requestAnimationFrame(update);
}

const heroStats = document.querySelector('.hero__stats');
if (heroStats) {
  new IntersectionObserver(([e]) => {
    if (e.isIntersecting) {
      document.querySelectorAll('.hero__stat-num').forEach(el =>
        animateCounter(el, parseInt(el.dataset.target)));
    }
  }, { threshold: 0.5 }).observe(heroStats);
}

const aboutStats = document.querySelector('.about__stats');
if (aboutStats) {
  new IntersectionObserver(([e]) => {
    if (e.isIntersecting) {
      document.querySelectorAll('.about__stat-num').forEach(el =>
        animateCounter(el, parseInt(el.dataset.target)));
    }
  }, { threshold: 0.5 }).observe(aboutStats);
}

// ── 6. Reveal on Scroll ────────────────────────────────────────────────────────
const revealEls = document.querySelectorAll('.reveal, .reveal-left, .reveal-right');
if (revealEls.length) {
  const obs = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        e.target.classList.add('visible');
        obs.unobserve(e.target);
      }
    });
  }, { threshold: 0.12 });
  revealEls.forEach(el => obs.observe(el));
}

// ── 7. Stagger children ───────────────────────────────────────────────────────
document.querySelectorAll('.stagger-child').forEach((el, i) => {
  el.style.setProperty('--i', i);
});

// ── 8. Helpers ────────────────────────────────────────────────────────────────
const FALLBACK_IMG = 'https://images.unsplash.com/photo-1568605114967-8130f3a36994?auto=format&fit=crop&w=600&q=80';

function resolveImg(url) {
  if (!url || url.trim() === '') return FALLBACK_IMG;
  if (url.startsWith('http')) return url;
  return `/uploads/${url}`;
}

function formatPrice(precio) {
  if (!precio || precio === 0) return 'Precio a consultar';
  return `$${Number(precio).toLocaleString('en-US')}`;
}

function parseAmenidades(raw) {
  if (!raw) return [];
  if (Array.isArray(raw)) return raw;
  try { return JSON.parse(raw); } catch { return []; }
}

// ── 9. Properties ─────────────────────────────────────────────────────────────
let allProperties = [];

async function fetchProperties() {
  const grid     = document.getElementById('propertiesGrid');
  const skeleton = document.getElementById('skeletonLoader');
  const empty    = document.getElementById('emptyState');

  skeleton.classList.remove('hidden');
  grid.classList.add('hidden');
  empty.classList.add('hidden');

  try {
    const res = await fetch('/api/crm/properties');
    if (!res.ok) throw new Error('API error');
    const data = await res.json();
    allProperties = Array.isArray(data) ? data : [];

    // Si no hay propiedades en el CRM, usar datos demo
    if (allProperties.length === 0) allProperties = getMockProperties();
  } catch {
    allProperties = getMockProperties();
  }

  skeleton.classList.add('hidden');
  renderProperties(allProperties);
}

function renderProperties(list) {
  const grid  = document.getElementById('propertiesGrid');
  const empty = document.getElementById('emptyState');

  grid.innerHTML = '';
  grid.classList.remove('hidden');
  empty.classList.add('hidden');

  if (!list.length) {
    empty.classList.remove('hidden');
    grid.classList.add('hidden');
    return;
  }

  list.forEach((prop, i) => grid.appendChild(createPropertyCard(prop, i)));
  AOS.refresh();
}

function createPropertyCard(prop, index) {
  const delay    = (index % 3) * 100;
  const precio   = formatPrice(prop.precio);
  const imgSrc   = resolveImg(prop.foto_portada_url);
  const opLower  = (prop.operacion || 'venta').toLowerCase();
  const opClass  = opLower === 'alquiler' ? 'alquiler' : 'venta';
  const titulo   = prop.titulo || prop.tipo_propiedad || 'Propiedad';
  const amenList = parseAmenidades(prop.amenidades);

  const specs = [
    prop.habitaciones    ? { icon: 'fa-bed',           text: `${prop.habitaciones} hab.` }  : null,
    prop.banos           ? { icon: 'fa-shower',        text: `${prop.banos} baños` }         : null,
    prop.metros_terreno  ? { icon: 'fa-mountain-sun',  text: prop.metros_terreno }            : null,
    prop.estacionamientos? { icon: 'fa-car',           text: `${prop.estacionamientos} est.`}: null,
  ].filter(Boolean);

  const card = document.createElement('div');
  card.className = 'prop-card';
  card.setAttribute('data-aos', 'fade-up');
  card.setAttribute('data-aos-delay', delay);
  card.dataset.propId = prop.id;

  card.innerHTML = `
    <div class="prop-card__img-wrap">
      <img class="prop-card__img"
           src="${imgSrc}"
           alt="${titulo}"
           loading="lazy"
           onerror="this.src='${FALLBACK_IMG}'">
      <span class="prop-card__badge prop-card__badge--${opClass}">${prop.operacion || 'Venta'}</span>
      ${amenList.length ? `<div class="prop-card__amenidad-preview">${amenList[0]}</div>` : ''}
    </div>
    <div class="prop-card__body">
      <div class="prop-card__tipo">${prop.tipo_propiedad || 'Propiedad'}</div>
      <h3 class="prop-card__titulo">${titulo}</h3>
      <div class="prop-card__pueblo"><i class="fa-solid fa-location-dot"></i>${prop.pueblo || ''}</div>
      <div class="prop-card__price">${precio}</div>
      ${specs.length ? `
        <div class="prop-card__specs">
          ${specs.map(s => `<span class="prop-card__spec"><i class="fa-solid ${s.icon}"></i>${s.text}</span>`).join('')}
        </div>` : ''}
    </div>`;

  card.addEventListener('click', () => openModal(prop));
  return card;
}

// ── 10. Filters ────────────────────────────────────────────────────────────────
const filterTipo   = document.getElementById('filterTipo');
const filterOp     = document.getElementById('filterOp');
const filterPueblo = document.getElementById('filterPueblo');
const clearBtn     = document.getElementById('clearFilters');

function debounce(fn, ms) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}

function applyFilters() {
  const tipo   = filterTipo.value.toLowerCase();
  const op     = filterOp.value.toLowerCase();
  const pueblo = filterPueblo.value.toLowerCase().trim();

  renderProperties(allProperties.filter(p => {
    const t = (p.tipo_propiedad || '').toLowerCase();
    const o = (p.operacion || '').toLowerCase();
    const l = ((p.pueblo || '') + ' ' + (p.direccion || '') + ' ' + (p.titulo || '')).toLowerCase();
    return (!tipo || t.includes(tipo)) && (!op || o.includes(op)) && (!pueblo || l.includes(pueblo));
  }));
}

filterTipo.addEventListener('change', applyFilters);
filterOp.addEventListener('change',   applyFilters);
filterPueblo.addEventListener('input', debounce(applyFilters, 300));
clearBtn.addEventListener('click', () => {
  filterTipo.value = filterOp.value = filterPueblo.value = '';
  renderProperties(allProperties);
});

// ── 11. Property Modal ────────────────────────────────────────────────────────
const modal      = document.getElementById('propertyModal');
const modalBody  = document.getElementById('modalBody');
const modalClose = document.getElementById('modalClose');
const modalBd    = document.getElementById('modalBackdrop');

function openModal(prop) {
  const precio   = formatPrice(prop.precio);
  const imgSrc   = resolveImg(prop.foto_portada_url);
  const opLower  = (prop.operacion || 'venta').toLowerCase();
  const opClass  = opLower === 'alquiler' ? 'alquiler' : 'venta';
  const titulo   = prop.titulo || prop.tipo_propiedad || 'Propiedad';
  const amenList = parseAmenidades(prop.amenidades);

  // Galeria de fotos extras
  let extrasJson = [];
  try { extrasJson = JSON.parse(prop.fotos_extras_urls || '[]'); } catch {}
  const extras = Array.isArray(extrasJson) ? extrasJson : [];

  const galeriaHtml = extras.length > 0 ? `
    <div class="modal-prop__galeria">
      ${extras.slice(0, 5).map(url => `
        <img src="${resolveImg(url)}" loading="lazy"
             onerror="this.src='${FALLBACK_IMG}'"
             onclick="this.closest('.modal-prop__galeria').querySelectorAll('img').forEach(i=>i.classList.remove('active'));this.classList.add('active');">
      `).join('')}
    </div>` : '';

  modalBody.innerHTML = `
    <div class="modal-prop__hero">
      <img class="modal-prop__img" src="${imgSrc}" alt="${titulo}"
           onerror="this.src='${FALLBACK_IMG}'">
      <span class="modal-prop__badge modal-prop__badge--${opClass}">${prop.operacion || 'Venta'}</span>
    </div>
    ${galeriaHtml}
    <div class="modal-prop__content">
      <div class="modal-prop__tipo">${prop.tipo_propiedad || ''}</div>
      <h2 class="modal-prop__titulo">${titulo}</h2>
      <div class="modal-prop__price">${precio}</div>
      ${prop.direccion ? `<div class="modal-prop__address"><i class="fa-solid fa-map-pin" style="color:var(--color-red);margin-right:6px;"></i>${prop.direccion}</div>` : ''}
      <div class="modal-prop__pueblo"><i class="fa-solid fa-location-dot" style="color:var(--color-red);margin-right:5px;"></i>${prop.pueblo || ''}, Puerto Rico</div>

      <div class="modal-prop__specs">
        ${prop.habitaciones     ? `<span class="modal-prop__spec"><i class="fa-solid fa-bed"></i>${prop.habitaciones} hab.</span>` : ''}
        ${prop.banos            ? `<span class="modal-prop__spec"><i class="fa-solid fa-shower"></i>${prop.banos} baños</span>` : ''}
        ${prop.metros_terreno   ? `<span class="modal-prop__spec"><i class="fa-solid fa-mountain-sun"></i>${prop.metros_terreno}</span>` : ''}
        ${prop.estacionamientos ? `<span class="modal-prop__spec"><i class="fa-solid fa-car"></i>${prop.estacionamientos} parking</span>` : ''}
      </div>

      ${prop.listing_description ? `<p class="modal-prop__desc">${prop.listing_description}</p>` : ''}

      ${amenList.length ? `
        <div class="modal-prop__amenidades">
          <div class="modal-prop__amenidades-title">Amenidades</div>
          <div class="modal-prop__amenidades-list">
            ${amenList.map(a => `<span class="modal-prop__amenidad"><i class="fa-solid fa-check"></i>${a}</span>`).join('')}
          </div>
        </div>` : ''}

      <div class="modal-prop__actions">
        <a href="#contacto" class="btn btn--primary" onclick="closeModal()">
          <i class="fa-solid fa-envelope"></i> Solicitar información
        </a>
        <a href="https://wa.me/17872086111?text=Hola%20Kelitza%2C%20me%20interesa%20la%20propiedad%3A%20${encodeURIComponent(titulo)}%20en%20${encodeURIComponent(prop.pueblo || '')}"
           target="_blank" rel="noopener" class="btn btn--gold">
          <i class="fa-brands fa-whatsapp"></i> WhatsApp
        </a>
      </div>
    </div>`;

  modal.classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeModal() {
  modal.classList.remove('open');
  document.body.style.overflow = '';
}

modalClose.addEventListener('click', closeModal);
modalBd.addEventListener('click',   closeModal);
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

// ── 12. Mortgage Calculator ───────────────────────────────────────────────────
const precioSlider = document.getElementById('precioSlider');
const downSlider   = document.getElementById('downSlider');
const tasaSlider   = document.getElementById('tasaSlider');
const toggleBtns   = document.querySelectorAll('.toggle-btn');

let calcState = { precio: 350000, down: 20, tasa: 6.5, plazo: 20 };
let animFrame;
let displayedPayment = 0;

const fmt    = n => Math.round(n).toLocaleString('en-US');
const fmtUSD = n => `$${fmt(n)}`;

function calcMortgage({ precio, down, tasa, plazo }) {
  const downAmt = precio * (down / 100);
  const loan    = precio - downAmt;
  const r       = (tasa / 100) / 12;
  const n       = plazo * 12;
  const monthly = r === 0 ? loan / n : loan * (r * Math.pow(1+r,n)) / (Math.pow(1+r,n)-1);
  return {
    monthly,
    loan,
    totalInterest: monthly * n - loan,
    totalCost:     monthly * n,
    principalPct:  (loan / (monthly * n)) * 100,
    downAmt,
  };
}

function animatePayment(target) {
  cancelAnimationFrame(animFrame);
  const from = displayedPayment, diff = target - from;
  const startTime = performance.now(), dur = 480;
  const step = (now) => {
    const t    = Math.min((now - startTime) / dur, 1);
    const ease = 1 - Math.pow(1 - t, 3);
    displayedPayment = from + diff * ease;
    document.getElementById('monthlyPayment').textContent = fmt(displayedPayment);
    if (t < 1) animFrame = requestAnimationFrame(step);
    else displayedPayment = target;
  };
  animFrame = requestAnimationFrame(step);
}

function updateSliderTrack(slider, min, max) {
  const pct = ((parseFloat(slider.value) - min) / (max - min)) * 100;
  slider.style.background =
    `linear-gradient(to right, var(--color-red) ${pct}%, rgba(255,255,255,0.12) ${pct}%)`;
}

function updateCalc() {
  const r = calcMortgage(calcState);
  document.getElementById('precioDisplay').textContent = fmtUSD(calcState.precio);
  document.getElementById('downDisplay').textContent   = `${calcState.down}% — ${fmtUSD(r.downAmt)}`;
  document.getElementById('tasaDisplay').textContent   = `${calcState.tasa.toFixed(1)}%`;
  animatePayment(r.monthly);
  document.getElementById('loanAmount').textContent    = fmtUSD(r.loan);
  document.getElementById('totalInterest').textContent = fmtUSD(r.totalInterest);
  document.getElementById('totalCost').textContent     = fmtUSD(r.totalCost);
  document.getElementById('principalBar').style.width  = `${r.principalPct.toFixed(1)}%`;
  document.getElementById('interestBar').style.width   = `${(100 - r.principalPct).toFixed(1)}%`;
  updateSliderTrack(precioSlider, 50000, 2000000);
  updateSliderTrack(downSlider,   3, 50);
  updateSliderTrack(tasaSlider,   1, 15);
}

precioSlider.addEventListener('input', () => { calcState.precio = parseInt(precioSlider.value);   updateCalc(); });
downSlider.addEventListener('input',   () => { calcState.down   = parseInt(downSlider.value);     updateCalc(); });
tasaSlider.addEventListener('input',   () => { calcState.tasa   = parseFloat(tasaSlider.value);   updateCalc(); });
toggleBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    toggleBtns.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    calcState.plazo = parseInt(btn.dataset.years);
    updateCalc();
  });
});

// ── 13. Contact Form — guarda en CRM ─────────────────────────────────────────
document.getElementById('contactForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const btn  = e.target.querySelector('button[type="submit"]');
  const orig = btn.innerHTML;
  const form = e.target;

  const nombre   = form.querySelector('[placeholder*="nombre"]')?.value || '';
  const telefono = form.querySelector('[placeholder*="eléfono"]')?.value || '';
  const email    = form.querySelector('[type="email"]')?.value || '';
  const interes  = form.querySelector('select')?.value || '';
  const mensaje  = form.querySelector('textarea')?.value || '';

  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Enviando...';
  btn.disabled  = true;

  try {
    await fetch('/api/crm/contacts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        nombre,
        email,
        telefono,
        fuente:  'Sitio Web Kelitza',
        notas:   `Interés: ${interes}\n\n${mensaje}`,
        empresa: '',
      }),
    });
    btn.innerHTML = '<i class="fa-solid fa-check"></i> ¡Mensaje enviado!';
    btn.style.background = '#16a34a';
    form.reset();
    setTimeout(() => {
      btn.innerHTML        = orig;
      btn.disabled         = false;
      btn.style.background = '';
    }, 3500);
  } catch {
    btn.innerHTML        = orig;
    btn.disabled         = false;
    btn.style.background = '';
    alert('Hubo un error. Contáctame directamente por WhatsApp.');
  }
});

// ── 14. Mock Properties (fallback demo) ──────────────────────────────────────
function getMockProperties() {
  return [
    {
      id: 1, titulo: 'Residencia moderna en Condado', tipo_propiedad: 'Casa', operacion: 'Venta',
      direccion: 'Urb. Condado Moderno #45', pueblo: 'San Juan',
      precio: 485000, habitaciones: 4, banos: 3, estacionamientos: 2,
      foto_portada_url: 'https://images.unsplash.com/photo-1564013799919-ab600027ffc6?auto=format&fit=crop&w=600&q=80',
      amenidades: JSON.stringify(['Piscina', 'Patio amplio', 'Seguridad 24/7']),
      listing_description: 'Hermosa residencia en una de las urbanizaciones más exclusivas de San Juan. Acabados de lujo, cocina remodelada y espacios amplios para toda la familia.',
    },
    {
      id: 2, titulo: 'Apartamento vista al mar', tipo_propiedad: 'Apartamento', operacion: 'Alquiler',
      direccion: 'Paseo Las Olas #302', pueblo: 'Isabela',
      precio: 1800, habitaciones: 2, banos: 2, estacionamientos: 1,
      foto_portada_url: 'https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?auto=format&fit=crop&w=600&q=80',
      amenidades: JSON.stringify(['Vista al mar', 'Balcón', 'Gimnasio']),
      listing_description: 'Moderno apartamento frente al mar en Isabela. Disfruta atardeceres únicos desde tu propio balcón privado.',
    },
    {
      id: 3, titulo: 'Penthouse de lujo Torre del Mar', tipo_propiedad: 'Penthouse', operacion: 'Venta',
      direccion: 'Torre del Mar PH-5', pueblo: 'Dorado',
      precio: 1250000, habitaciones: 3, banos: 3, estacionamientos: 2,
      foto_portada_url: 'https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?auto=format&fit=crop&w=600&q=80',
      amenidades: JSON.stringify(['Vista panorámica', 'Jacuzzi', 'Terraza privada', 'Concierge']),
      listing_description: 'Penthouse de ultra-lujo con vista de 360° al océano Atlántico. Una oportunidad única para vivir en la cima de Dorado.',
    },
    {
      id: 4, titulo: 'Solar en Urb. Lumar, Boquerón', tipo_propiedad: 'Solar', operacion: 'Venta',
      direccion: 'Urb. Lumar', pueblo: 'Cabo Rojo',
      precio: 95000, metros_terreno: '0.25 cdas.',
      foto_portada_url: 'https://images.unsplash.com/photo-1500382017468-9049fed747ef?auto=format&fit=crop&w=600&q=80',
      amenidades: JSON.stringify(['Cerca de la playa', 'Esquinero', 'Acceso carretera']),
    },
    {
      id: 5, titulo: 'Terreno 13 cuerdas con vistas', tipo_propiedad: 'Terreno', operacion: 'Venta',
      direccion: 'Carr. 119', pueblo: 'San Germán',
      precio: 320000, metros_terreno: '13.15 cdas.',
      foto_portada_url: 'https://images.unsplash.com/photo-1500382017468-9049fed747ef?auto=format&fit=crop&w=600&q=80',
      amenidades: JSON.stringify(['Vista panorámica', 'Acceso agua y luz']),
      listing_description: 'Terreno de 13.15 cuerdas con impresionantes vistas de las montañas del suroeste de Puerto Rico.',
    },
    {
      id: 6, titulo: 'Terreno boscoso en Loíza', tipo_propiedad: 'Terreno', operacion: 'Venta',
      direccion: 'Carr. 188', pueblo: 'Loíza',
      precio: 0, metros_terreno: 'Gran extensión',
      foto_portada_url: 'https://images.unsplash.com/photo-1448375240586-882707db888b?auto=format&fit=crop&w=600&q=80',
      amenidades: JSON.stringify(['Eco-turismo', 'Potencial agrícola']),
      listing_description: 'Extenso terreno boscoso con gran potencial para proyectos eco-turísticos o agrícolas.',
    },
  ];
}

// ── Init ──────────────────────────────────────────────────────────────────────
fetchProperties();
updateCalc();
