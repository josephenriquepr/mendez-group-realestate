import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Img,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
  staticFile,
  spring,
  Easing,
} from 'remotion';
import {
  TransitionSeries,
  linearTiming,
  springTiming,
} from '@remotion/transitions';
import { fade }      from '@remotion/transitions/fade';
import { slide }     from '@remotion/transitions/slide';
import { wipe }      from '@remotion/transitions/wipe';
import { flip }      from '@remotion/transitions/flip';
import { clockWipe } from '@remotion/transitions/clock-wipe';
import { z }         from 'zod';

// ─── Schema ───────────────────────────────────────────────────────────────────

export const reelSchema = z.object({
  photos:            z.array(z.string()),
  precio:            z.number().nullable().optional(),
  tipo:              z.string().optional(),
  operacion:         z.string().optional(),
  direccion:         z.string().optional(),
  pueblo:            z.string().optional(),
  habitaciones:      z.number().nullable().optional(),
  banos:             z.number().nullable().optional(),
  pies_cuadrados:    z.number().nullable().optional(),
  estacionamientos:  z.number().nullable().optional(),
  agente_nombre:     z.string().optional(),
  agente_licencia:   z.string().optional(),
  agente_telefono:   z.string().optional(),
  hasMusic:          z.boolean().optional(),
  seed:              z.number().optional(),
  tema:              z.number().optional(),
  agencia_tagline:   z.string().nullable().optional(),
  color_primario:    z.string().nullable().optional(),
  color_acento:      z.string().nullable().optional(),
  logo_path:         z.string().nullable().optional(),
});

export type ReelProps = z.infer<typeof reelSchema>;

// ─── Constants ────────────────────────────────────────────────────────────────

export const PHOTO_FRAMES   = 90;   // 3 sec @ 30fps
export const CONTACT_FRAMES = 90;
export const TRANSITION_FRAMES = 20;

// ─── Transition picker (cycles through 5 styles per tema) ────────────────────

function getTransition(index: number, tema: number) {
  const style = (index + tema) % 5;
  const timing = springTiming({ durationInFrames: TRANSITION_FRAMES, config: { damping: 200 } });
  const ltiming = linearTiming({ durationInFrames: TRANSITION_FRAMES });
  switch (style) {
    case 0: return { presentation: fade(), timing: ltiming };
    case 1: return { presentation: slide({ direction: 'from-right' }), timing };
    case 2: return { presentation: wipe({ direction: 'from-bottom-right' }), timing };
    case 3: return { presentation: flip({ direction: 'from-left' }), timing };
    case 4: return { presentation: clockWipe({ width: 1080, height: 1920 }), timing: ltiming };
    default: return { presentation: fade(), timing: ltiming };
  }
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function fmtMoney(n: number | null | undefined): string {
  if (!n) return '';
  return '$' + n.toLocaleString('en-US');
}

function hexRgb(hex: string) {
  const h = hex.replace('#', '');
  return { r: parseInt(h.slice(0,2),16), g: parseInt(h.slice(2,4),16), b: parseInt(h.slice(4,6),16) };
}

// ─── Ken Burns photo wrapper ──────────────────────────────────────────────────

const KenBurns: React.FC<{ src: string; direction?: 'in' | 'out' }> = ({ src, direction = 'in' }) => {
  const frame = useCurrentFrame();
  const scale = direction === 'in'
    ? interpolate(frame, [0, PHOTO_FRAMES], [1, 1.08], { extrapolateRight: 'clamp' })
    : interpolate(frame, [0, PHOTO_FRAMES], [1.08, 1], { extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ overflow: 'hidden' }}>
      <Img
        src={staticFile(src)}
        style={{
          width: '100%', height: '100%', objectFit: 'cover',
          transform: `scale(${scale})`,
          transformOrigin: direction === 'in' ? 'center center' : '30% 40%',
        }}
      />
    </AbsoluteFill>
  );
};

// ─── Hero slide ───────────────────────────────────────────────────────────────

const HeroSlide: React.FC<{ props: ReelProps; primary: string; accent: string }> = ({ props, primary, accent }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { r: ar, g: ag, b: ab } = hexRgb(accent);

  const slideUp = spring({ fps, frame, config: { damping: 18, stiffness: 80 }, from: 60, to: 0 });
  const fadeIn  = interpolate(frame, [0, 15], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill>
      <KenBurns src={props.photos![0]} direction="in" />

      {/* Gradient overlay */}
      <AbsoluteFill style={{
        background: 'linear-gradient(to bottom, rgba(0,0,0,0.2) 0%, transparent 35%, rgba(0,0,0,0.5) 60%, rgba(0,0,0,0.88) 100%)',
      }} />

      {/* Top bar */}
      <div style={{
        position: 'absolute', top: 55, left: 44, right: 44,
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        opacity: fadeIn, transform: `translateY(${Math.max(0, -slideUp + 60)}px)`,
      }}>
        <div style={{
          background: primary, borderRadius: 50,
          padding: '13px 30px', color: '#fff',
          fontSize: 33, fontWeight: 800,
          fontFamily: 'system-ui, -apple-system, sans-serif',
          letterSpacing: 1.5,
        }}>
          {(props.operacion || 'Venta').toUpperCase()}
        </div>
        {props.agencia_tagline && (
          <div style={{
            background: 'rgba(255,255,255,0.14)',
            backdropFilter: 'blur(10px)',
            borderRadius: 50, padding: '13px 26px',
            color: '#fff', fontSize: 26, fontWeight: 600,
            fontFamily: 'system-ui, sans-serif',
            border: '1.5px solid rgba(255,255,255,0.28)',
          }}>
            {props.agencia_tagline}
          </div>
        )}
      </div>

      {/* Bottom info */}
      <div style={{
        position: 'absolute', bottom: 0, left: 0, right: 0,
        padding: '0 48px 72px',
        transform: `translateY(${slideUp}px)`,
        opacity: fadeIn,
      }}>
        {props.precio && (
          <div style={{
            color: `rgb(${ar},${ag},${ab})`, fontSize: 82, fontWeight: 900,
            fontFamily: 'system-ui, sans-serif',
            textShadow: '0 3px 24px rgba(0,0,0,0.7)',
            lineHeight: 1, marginBottom: 10,
          }}>
            {fmtMoney(props.precio)}
          </div>
        )}
        <div style={{
          color: '#fff', fontSize: 40, fontWeight: 700,
          fontFamily: 'system-ui, sans-serif', marginBottom: 6,
          textShadow: '0 2px 12px rgba(0,0,0,0.5)',
        }}>
          {props.tipo} · {props.pueblo}
        </div>
        <div style={{
          color: 'rgba(255,255,255,0.82)', fontSize: 29,
          fontFamily: 'system-ui, sans-serif', marginBottom: 22,
          textShadow: '0 1px 8px rgba(0,0,0,0.4)',
        }}>
          {props.direccion}
        </div>
        <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap' }}>
          {[
            props.habitaciones && { icon: '🛏', val: `${props.habitaciones} Hab.` },
            props.banos        && { icon: '🚿', val: `${props.banos} Baños` },
            props.pies_cuadrados && { icon: '📐', val: `${props.pies_cuadrados!.toLocaleString()} p²` },
            props.estacionamientos && { icon: '🚗', val: `${props.estacionamientos} Est.` },
          ].filter(Boolean).map((s: any, i: number) => (
            <div key={i} style={{
              background: 'rgba(255,255,255,0.16)',
              backdropFilter: 'blur(8px)',
              borderRadius: 18, padding: '10px 20px',
              color: '#fff', fontSize: 27, fontWeight: 700,
              fontFamily: 'system-ui, sans-serif',
              border: '1px solid rgba(255,255,255,0.22)',
            }}>
              {s.icon} {s.val}
            </div>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ─── Extra photo slide ────────────────────────────────────────────────────────

const PhotoSlide: React.FC<{ photo: string; index: number; total: number; primary: string }> = ({
  photo, index, total, primary,
}) => {
  const frame = useCurrentFrame();
  const fadeIn = interpolate(frame, [0, 12], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ opacity: fadeIn }}>
      <KenBurns src={photo} direction={index % 2 === 0 ? 'in' : 'out'} />
      <AbsoluteFill style={{ background: 'linear-gradient(to bottom, rgba(0,0,0,0.32) 0%, transparent 25%)' }} />
      <div style={{
        position: 'absolute', top: 48, right: 48,
        background: primary, borderRadius: 50,
        padding: '12px 26px', color: '#fff',
        fontSize: 30, fontWeight: 700,
        fontFamily: 'system-ui, sans-serif',
        boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
      }}>
        {index + 2} / {total}
      </div>
    </AbsoluteFill>
  );
};

// ─── Contact slide ────────────────────────────────────────────────────────────

const ContactSlide: React.FC<{ props: ReelProps; primary: string; accent: string }> = ({ props, primary, accent }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const slideUp = spring({ fps, frame, config: { damping: 16, stiffness: 65 }, from: 80, to: 0 });
  const fadeIn  = interpolate(frame, [0, 18], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  const logoSrc = props.logo_path ? staticFile(props.logo_path) : null;
  const tagline = props.agencia_tagline || 'Bienes Raíces · Puerto Rico';
  const { r: ar, g: ag, b: ab } = hexRgb(accent);

  return (
    <AbsoluteFill style={{
      background: `linear-gradient(160deg, ${primary} 0%, #0a2a38 55%, #050f15 100%)`,
      opacity: fadeIn,
    }}>
      {/* Decorative lines */}
      <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', opacity: 0.06 }}>
        {Array.from({ length: 10 }, (_, i) => (
          <line key={i}
            x1={-150 + i * 160} y1="0"
            x2={500 + i * 160} y2="1920"
            stroke="#fff" strokeWidth="70"
          />
        ))}
      </svg>

      {/* Centered content */}
      <div style={{
        position: 'absolute', inset: 0,
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
        padding: '0 60px',
        transform: `translateY(${slideUp}px)`,
      }}>
        {/* Logo circle */}
        {logoSrc ? (
          <div style={{
            width: 180, height: 180, borderRadius: '50%',
            overflow: 'hidden', marginBottom: 40,
            border: `5px solid rgb(${ar},${ag},${ab})`,
            boxShadow: `0 8px 40px rgba(${ar},${ag},${ab},0.4)`,
          }}>
            <Img src={logoSrc} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
          </div>
        ) : (
          <div style={{
            width: 130, height: 6,
            background: `rgb(${ar},${ag},${ab})`,
            borderRadius: 4, marginBottom: 48,
            boxShadow: `0 4px 20px rgba(${ar},${ag},${ab},0.5)`,
          }} />
        )}

        {/* Agent name */}
        <div style={{
          color: '#fff', fontSize: 66, fontWeight: 900,
          fontFamily: 'system-ui, sans-serif',
          textAlign: 'center', lineHeight: 1.1,
          textShadow: '0 3px 20px rgba(0,0,0,0.35)',
          marginBottom: 10,
        }}>
          {props.agente_nombre || 'Agente ListaPro'}
        </div>

        {props.agente_licencia && (
          <div style={{
            color: 'rgba(255,255,255,0.6)', fontSize: 28,
            fontFamily: 'system-ui, sans-serif',
            marginBottom: 36,
          }}>
            Lic. {props.agente_licencia}
          </div>
        )}

        {/* Divider */}
        <div style={{
          width: 100, height: 4,
          background: `rgb(${ar},${ag},${ab})`,
          borderRadius: 4, marginBottom: 36,
        }} />

        {/* Tagline */}
        <div style={{
          color: 'rgba(255,255,255,0.82)', fontSize: 32,
          fontFamily: 'system-ui, sans-serif', fontWeight: 600,
          textAlign: 'center', marginBottom: 48,
          letterSpacing: 0.5,
        }}>
          {tagline}
        </div>

        {/* Phone pill */}
        {props.agente_telefono && (
          <div style={{
            background: `rgb(${ar},${ag},${ab})`,
            borderRadius: 24, padding: '22px 52px',
            color: '#1c2b35', fontSize: 50, fontWeight: 900,
            fontFamily: 'system-ui, sans-serif',
            letterSpacing: 2,
            boxShadow: `0 8px 32px rgba(${ar},${ag},${ab},0.45)`,
          }}>
            📞 {props.agente_telefono}
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};

// ─── Main composition ─────────────────────────────────────────────────────────

export const PropertyReel: React.FC<ReelProps> = (props) => {
  const { photos = [], hasMusic, tema = 0, color_primario, color_acento } = props;

  const primary = color_primario || '#1a6b8a';
  const accent  = color_acento  || '#f4a623';

  const musicSrc = staticFile('audio/music.mp3');

  // Build slides list
  type Slide = { component: React.ReactNode; durationInFrames: number };
  const slides: Slide[] = [];

  // Hero
  slides.push({
    component: <HeroSlide props={props} primary={primary} accent={accent} />,
    durationInFrames: PHOTO_FRAMES,
  });

  // Extra photos
  photos.slice(1).forEach((photo, i) => {
    slides.push({
      component: <PhotoSlide photo={photo} index={i} total={photos.length} primary={primary} />,
      durationInFrames: PHOTO_FRAMES,
    });
  });

  // Contact
  slides.push({
    component: <ContactSlide props={props} primary={primary} accent={accent} />,
    durationInFrames: CONTACT_FRAMES,
  });

  // Total duration for music volume fade-out
  const totalFrames = slides.reduce((s, sl) => s + sl.durationInFrames, 0)
    - TRANSITION_FRAMES * (slides.length - 1);

  return (
    <AbsoluteFill style={{ background: '#000' }}>
      {/* Background music */}
      {hasMusic && (
        <Audio
          src={musicSrc}
          startFrom={0}
          volume={(f) =>
            interpolate(
              f,
              [0, 15, totalFrames - 30, totalFrames],
              [0, 0.35, 0.35, 0],
              { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
            )
          }
        />
      )}

      {/* Slide show with transitions */}
      <TransitionSeries>
        {slides.map((slide, i) => {
          const t = getTransition(i, tema);
          return (
            <React.Fragment key={i}>
              <TransitionSeries.Sequence durationInFrames={slide.durationInFrames}>
                {slide.component}
              </TransitionSeries.Sequence>
              {i < slides.length - 1 && (
                <TransitionSeries.Transition
                  presentation={t.presentation}
                  timing={t.timing}
                />
              )}
            </React.Fragment>
          );
        })}
      </TransitionSeries>
    </AbsoluteFill>
  );
};
