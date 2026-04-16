/* ============================================
   MENDEZ GROUP — Website JavaScript
   ============================================ */

'use strict';

// ── 1. AOS Init ──────────────────────────────────────────────────────────────
AOS.init({
  duration: 700,
  easing: 'ease-out-cubic',
  once: true,
  offset: 60,
});

// ── 2. Navbar scroll effect ──────────────────────────────────────────────────
const navbar    = document.getElementById('navbar');
const sentinel  = document.getElementById('nav-sentinel');

const navObserver = new IntersectionObserver(
  ([entry]) => navbar.classList.toggle('scrolled', !entry.isIntersecting),
  { threshold: 0 }
);
navObserver.observe(sentinel);

// Hamburger menu
const hamburger = document.getElementById('hamburger');
const navLinks  = document.getElementById('navLinks');

hamburger.addEventListener('click', () => {
  hamburger.classList.toggle('open');
  navLinks.classList.toggle('open');
});

navLinks.querySelectorAll('.nav__link').forEach(link => {
  link.addEventListener('click', () => {
    hamburger.classList.remove('open');
    navLinks.classList.remove('open');
  });
});

// ── 3. Hero Parallax ─────────────────────────────────────────────────────────
const heroBg = document.getElementById('heroBg');

function handleParallax() {
  const scrollY    = window.scrollY;
  const maxOffset  = window.innerHeight * 0.3;
  const offset     = Math.min(scrollY * 0.35, maxOffset);
  heroBg.style.transform = `translateY(${offset}px) scale(1.1)`;
}
window.addEventListener('scroll', handleParallax, { passive: true });

// ── 4. Hero Stats Counter ─────────────────────────────────────────────────────
function animateCounter(el, target, duration = 1800) {
  const start  = performance.now();
  const update = (time) => {
    const progress = Math.min((time - start) / duration, 1);
    const ease     = 1 - Math.pow(1 - progress, 3);           // ease-out-cubic
    el.textContent = Math.round(target * ease).toLocaleString();
    if (progress < 1) requestAnimationFrame(update);
  };
  requestAnimationFrame(update);
}

const heroStats = document.querySelector('.hero__stats');
if (heroStats) {
  const statsObserver = new IntersectionObserver(([entry]) => {
    if (entry.isIntersecting) {
      document.querySelectorAll('.hero__stat-num').forEach(el => {
        animateCounter(el, parseInt(el.dataset.target));
      });
      statsObserver.disconnect();
    }
  }, { threshold: 0.5 });
  statsObserver.observe(heroStats);
}

// ── 5. Properties ─────────────────────────────────────────────────────────────
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
    allProperties = await res.json();
  } catch {
    // Fallback: demo properties when backend isn't reachable
    allProperties = getMockProperties();
  } finally {
    skeleton.classList.add('hidden');
    renderProperties(allProperties);
  }
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
  const delay   = (index % 3) * 100;
  const price   = prop.precio
    ? `$${Number(prop.precio).toLocaleString('en-US')}`
    : 'Precio a consultar';
  const imgSrc  = resolveImg(prop.foto_portada_url,
    'https://images.unsplash.com/photo-1568605114967-8130f3a36994?auto=format&fit=crop&w=600&q=80');
  const opLower = (prop.operacion || 'venta').toLowerCase();
  const opClass = opLower === 'alquiler' ? 'alquiler' : 'venta';

  const specs = [
    prop.habitaciones                  ? `🛏️ ${prop.habitaciones} hab.`                                     : null,
    prop.banos                         ? `🚿 ${prop.banos} baños`                                           : null,
    prop.pies_cuadrados_construccion   ? `📐 ${Number(prop.pies_cuadrados_construccion).toLocaleString()} ft²` : null,
    prop.estacionamientos              ? `🚗 ${prop.estacionamientos}`                                      : null,
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
           alt="${prop.tipo_propiedad || 'Propiedad'} en ${prop.pueblo || ''}"
           loading="lazy"
           onerror="this.src='https://images.unsplash.com/photo-1568605114967-8130f3a36994?auto=format&fit=crop&w=600&q=80'">
      <span class="prop-card__badge prop-card__badge--${opClass}">${prop.operacion || 'Venta'}</span>
    </div>
    <div class="prop-card__body">
      <div class="prop-card__tipo">${prop.tipo_propiedad || 'Propiedad'}</div>
      <div class="prop-card__address">${prop.direccion || 'Dirección disponible'}</div>
      <div class="prop-card__pueblo">📍 ${prop.pueblo || ''}</div>
      <div class="prop-card__price">${price}</div>
      ${specs.length ? `
        <div class="prop-card__specs">
          ${specs.map(s => `<span class="prop-card__spec">${s}</span>`).join('')}
        </div>` : ''}
    </div>`;

  card.addEventListener('click', () => openModal(prop));
  return card;
}

function resolveImg(url, fallback) {
  if (!url) return fallback;
  if (url.startsWith('http')) return url;
  return `/uploads/${url}`;
}

// ── 6. Filters ────────────────────────────────────────────────────────────────
const filterTipo   = document.getElementById('filterTipo');
const filterOp     = document.getElementById('filterOp');
const filterPueblo = document.getElementById('filterPueblo');
const clearBtn     = document.getElementById('clearFilters');

function applyFilters() {
  const tipo   = filterTipo.value.toLowerCase();
  const op     = filterOp.value.toLowerCase();
  const pueblo = filterPueblo.value.toLowerCase().trim();

  renderProperties(allProperties.filter(p => {
    const t = (p.tipo_propiedad || '').toLowerCase();
    const o = (p.operacion || '').toLowerCase();
    const l = ((p.pueblo || '') + ' ' + (p.direccion || '')).toLowerCase();
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

function debounce(fn, ms) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}

// ── 7. Property Modal ─────────────────────────────────────────────────────────
const modal      = document.getElementById('propertyModal');
const modalBody  = document.getElementById('modalBody');
const modalClose = document.getElementById('modalClose');
const modalBd    = document.getElementById('modalBackdrop');

function openModal(prop) {
  const price   = prop.precio
    ? `$${Number(prop.precio).toLocaleString('en-US')}`
    : 'Precio a consultar';
  const imgSrc  = resolveImg(prop.foto_portada_url,
    'https://images.unsplash.com/photo-1568605114967-8130f3a36994?auto=format&fit=crop&w=800&q=80');
  const opLower = (prop.operacion || 'venta').toLowerCase();
  const opClass = opLower === 'alquiler' ? 'alquiler' : 'venta';

  const amenidades = (() => {
    if (!prop.amenidades) return [];
    if (Array.isArray(prop.amenidades)) return prop.amenidades;
    try { return JSON.parse(prop.amenidades); } catch { return []; }
  })();

  modalBody.innerHTML = `
    <img class="modal-prop__img" src="${imgSrc}" alt="${prop.tipo_propiedad || 'Propiedad'}"
         onerror="this.src='https://images.unsplash.com/photo-1568605114967-8130f3a36994?auto=format&fit=crop&w=800&q=80'">
    <span class="modal-prop__badge modal-prop__badge--${opClass}">${prop.operacion || 'Venta'}</span>
    <div class="modal-prop__price">${price}</div>
    <div class="modal-prop__address">${prop.direccion || ''}</div>
    <div class="modal-prop__pueblo">📍 ${prop.pueblo || ''}</div>
    <div class="modal-prop__specs">
      ${prop.habitaciones                ? `<span class="modal-prop__spec">🛏️ ${prop.habitaciones} hab.</span>` : ''}
      ${prop.banos                       ? `<span class="modal-prop__spec">🚿 ${prop.banos} baños</span>`       : ''}
      ${prop.pies_cuadrados_construccion ? `<span class="modal-prop__spec">📐 ${Number(prop.pies_cuadrados_construccion).toLocaleString()} ft²</span>` : ''}
      ${prop.estacionamientos            ? `<span class="modal-prop__spec">🚗 ${prop.estacionamientos} parking</span>` : ''}
      ${prop.metros_o_cuerdas_terreno    ? `<span class="modal-prop__spec">🌿 ${prop.metros_o_cuerdas_terreno} cuerdas</span>` : ''}
    </div>
    ${prop.listing_description ? `<p class="modal-prop__desc">${prop.listing_description}</p>` : ''}
    ${amenidades.length ? `
      <div class="modal-prop__amenidades">
        ${amenidades.map(a => `<span class="modal-prop__amenidad">${a}</span>`).join('')}
      </div>` : ''}
    ${prop.nombre_agente ? `
      <div style="padding:16px;background:#f7f9fb;border-radius:12px;margin-bottom:16px;">
        <small style="font-size:0.75rem;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#6b7f8a;">Agente</small>
        <div style="font-weight:700;margin-top:4px;">${prop.nombre_agente}</div>
        ${prop.telefono_agente ? `<div style="color:#1a6b8a;margin-top:2px;">📞 ${prop.telefono_agente}</div>` : ''}
      </div>` : ''}
    <a href="#contacto" class="btn btn--primary btn--full" onclick="closeModal()">Solicitar información →</a>`;

  modal.classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeModal() {
  modal.classList.remove('open');
  document.body.style.overflow = '';
}

modalClose.addEventListener('click', closeModal);
modalBd.addEventListener('click', closeModal);
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

// ── 8. Mortgage Calculator ────────────────────────────────────────────────────
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

  const monthly = r === 0
    ? loan / n
    : loan * (r * Math.pow(1 + r, n)) / (Math.pow(1 + r, n) - 1);

  const totalPaid     = monthly * n;
  const totalInterest = totalPaid - loan;
  const principalPct  = (loan / totalPaid) * 100;

  return { monthly, loan, totalInterest, totalCost: totalPaid, principalPct, downAmt };
}

function animatePayment(target) {
  cancelAnimationFrame(animFrame);
  const from      = displayedPayment;
  const diff      = target - from;
  const startTime = performance.now();
  const dur       = 480;

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
    `linear-gradient(to right, var(--color-gold) ${pct}%, rgba(255,255,255,0.15) ${pct}%)`;
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

  const pPct = r.principalPct.toFixed(1);
  const iPct = (100 - r.principalPct).toFixed(1);
  document.getElementById('principalBar').style.width = `${pPct}%`;
  document.getElementById('interestBar').style.width  = `${iPct}%`;

  updateSliderTrack(precioSlider, 50000, 2000000);
  updateSliderTrack(downSlider,   3,     50);
  updateSliderTrack(tasaSlider,   1,     15);
}

precioSlider.addEventListener('input', () => { calcState.precio = parseInt(precioSlider.value); updateCalc(); });
downSlider.addEventListener('input',   () => { calcState.down   = parseInt(downSlider.value);   updateCalc(); });
tasaSlider.addEventListener('input',   () => { calcState.tasa   = parseFloat(tasaSlider.value); updateCalc(); });

toggleBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    toggleBtns.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    calcState.plazo = parseInt(btn.dataset.years);
    updateCalc();
  });
});

// ── 9. Contact Form ───────────────────────────────────────────────────────────
document.getElementById('contactForm').addEventListener('submit', e => {
  e.preventDefault();
  const btn = e.target.querySelector('button[type="submit"]');
  btn.textContent = '✓ Mensaje enviado';
  btn.disabled = true;
  btn.style.background = '#28a745';
  setTimeout(() => {
    btn.textContent = 'Enviar Mensaje';
    btn.disabled = false;
    btn.style.background = '';
    e.target.reset();
  }, 3000);
});

// ── 10. Mock properties (demo fallback) ───────────────────────────────────────
function getMockProperties() {
  return [
    {
      id: 1, tipo_propiedad: 'Casa', operacion: 'Venta',
      direccion: 'Urb. Condado Moderno #45', pueblo: 'San Juan',
      precio: 485000, habitaciones: 4, banos: 3,
      pies_cuadrados_construccion: 2400, estacionamientos: 2,
      foto_portada_url: 'https://images.unsplash.com/photo-1564013799919-ab600027ffc6?auto=format&fit=crop&w=600&q=80',
      amenidades: ['Piscina', 'Patio amplio', 'Seguridad 24/7'],
      nombre_agente: 'Carlos Méndez', telefono_agente: '(787) 555-0101',
      listing_description: 'Hermosa residencia en una de las urbanizaciones más exclusivas de San Juan. Cuenta con acabados de lujo, cocina remodelada y espacios amplios para toda la familia.',
    },
    {
      id: 2, tipo_propiedad: 'Apartamento', operacion: 'Alquiler',
      direccion: 'Paseo Las Olas #302', pueblo: 'Isabela',
      precio: 1800, habitaciones: 2, banos: 2,
      pies_cuadrados_construccion: 1100, estacionamientos: 1,
      foto_portada_url: 'https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?auto=format&fit=crop&w=600&q=80',
      amenidades: ['Vista al mar', 'Balcón', 'Gimnasio'],
      nombre_agente: 'Ana Torres', telefono_agente: '(787) 555-0102',
      listing_description: 'Moderno apartamento frente al mar en Isabela. Disfruta de atardeceres únicos desde tu propio balcón privado.',
    },
    {
      id: 3, tipo_propiedad: 'Penthouse', operacion: 'Venta',
      direccion: 'Torre del Mar PH-5', pueblo: 'Dorado',
      precio: 1250000, habitaciones: 3, banos: 3,
      pies_cuadrados_construccion: 3200, estacionamientos: 2,
      foto_portada_url: 'https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?auto=format&fit=crop&w=600&q=80',
      amenidades: ['Vista panorámica', 'Jacuzzi', 'Terraza privada', 'Concierge'],
      nombre_agente: 'Carlos Méndez', telefono_agente: '(787) 555-0101',
      listing_description: 'Penthouse de ultra-lujo con vista de 360° al océano Atlántico. Una oportunidad única para vivir en la cima de Dorado.',
    },
    {
      id: 4, tipo_propiedad: 'Solar', operacion: 'Venta',
      direccion: 'Carr. 111 Km 3.2', pueblo: 'Aguadilla',
      precio: 95000, habitaciones: null, banos: null,
      metros_o_cuerdas_terreno: 1.5,
      foto_portada_url: 'https://images.unsplash.com/photo-1500382017468-9049fed747ef?auto=format&fit=crop&w=600&q=80',
      amenidades: ['Vista al mar', 'Esquinero', 'Acceso carretera'],
      nombre_agente: 'José Rivera', telefono_agente: '(787) 555-0103',
    },
    {
      id: 5, tipo_propiedad: 'Casa', operacion: 'Venta',
      direccion: 'Urb. Estancias del Sur #12', pueblo: 'Ponce',
      precio: 325000, habitaciones: 3, banos: 2,
      pies_cuadrados_construccion: 1850, estacionamientos: 2,
      foto_portada_url: 'https://images.unsplash.com/photo-1568605114967-8130f3a36994?auto=format&fit=crop&w=600&q=80',
      amenidades: ['Patio trasero', 'Marquesina techada'],
      nombre_agente: 'Ana Torres', telefono_agente: '(787) 555-0102',
    },
    {
      id: 6, tipo_propiedad: 'Comercial', operacion: 'Alquiler',
      direccion: 'Av. Gautier Benítez Local 3', pueblo: 'Caguas',
      precio: 3500, habitaciones: null, banos: 2,
      pies_cuadrados_construccion: 1500,
      foto_portada_url: 'https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=600&q=80',
      amenidades: ['Estacionamiento', 'A/C central', 'Bodega incluida'],
      nombre_agente: 'José Rivera', telefono_agente: '(787) 555-0103',
    },
  ];
}

// ── Init ──────────────────────────────────────────────────────────────────────
fetchProperties();
updateCalc();
