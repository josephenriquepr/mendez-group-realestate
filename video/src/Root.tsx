import React from 'react';
import { Composition } from 'remotion';
import { PropertyReel, reelSchema } from './PropertyReel';

const DEFAULT_PHOTOS = ['assets/photo_0.jpg'];
const PHOTO_DURATION = 90;
const CONTACT_DURATION = 90;

export const Root: React.FC = () => {
  return (
    <Composition
      id="PropertyReel"
      component={PropertyReel}
      fps={30}
      width={1080}
      height={1920}
      schema={reelSchema}
      defaultProps={{
        photos:           DEFAULT_PHOTOS,
        precio:           350000,
        tipo:             'Casa',
        operacion:        'Venta',
        direccion:        'Calle Rosa #12, Urb. Jardines del Caribe',
        pueblo:           'San Juan',
        habitaciones:     3,
        banos:            2,
        pies_cuadrados:   1500,
        estacionamientos: 2,
        agente_nombre:    'Kelitza Méndez',
        agente_licencia:  'LIC-1234',
        agente_telefono:  '787-000-0000',
        hasMusic:         false,
        seed:             42,
        tema:             0,
        agencia_tagline:  'Bienes Raíces · Puerto Rico',
        color_primario:   null,
        color_acento:     null,
        logo_path:        null,
      }}
      calculateMetadata={async ({ props }) => {
        const n = props.photos?.length ?? 1;
        const total = n * PHOTO_DURATION + CONTACT_DURATION;
        return { durationInFrames: total };
      }}
    />
  );
};
