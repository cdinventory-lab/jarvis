import React from 'react';

const S = ({ children, size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.3"
    strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{children}</svg>
);

export const Icons = {
  spark: (p) => <S {...p}><path d="M12 3v4M12 17v4M5 12H3M21 12h-2M6.3 6.3 4.9 4.9M19.1 19.1l-1.4-1.4M17.7 6.3l1.4-1.4M4.9 19.1l1.4-1.4" /><circle cx="12" cy="12" r="3.2" /></S>,
  text2img: (p) => <S {...p}><rect x="3" y="4" width="18" height="16" rx="1" /><path d="M3 16l5-5 4 4 3-3 6 6" /><path d="M8 8h4" /></S>,
  img2img: (p) => <S {...p}><rect x="3" y="3" width="8" height="8" /><rect x="13" y="13" width="8" height="8" /><path d="M13 7h8M17 3v8M3 17h8M7 21v-8" /></S>,
  mockup: (p) => <S {...p}><path d="M9 3 5 5 3 11l3 1v9h12v-9l3-1-2-6-4-2-3 3z" /></S>,
  logo: (p) => <S {...p}><circle cx="12" cy="12" r="9" /><path d="M12 5v14M5 12h14" /><circle cx="12" cy="12" r="3" /></S>,
  photoshoot: (p) => <S {...p}><rect x="2.5" y="6" width="19" height="14" rx="2" /><circle cx="12" cy="13" r="4" /><path d="M8 6l1.5-2h5L16 6" /></S>,
  video: (p) => <S {...p}><rect x="2.5" y="5" width="13" height="14" rx="2" /><path d="M15.5 10l6-3v10l-6-3z" /></S>,
  vector: (p) => <S {...p}><path d="M4 20 20 4" /><rect x="2" y="17" width="5" height="5" /><rect x="17" y="2" width="5" height="5" /><path d="M9 8c3-2 5 2 7 0" /></S>,
  techpack: (p) => <S {...p}><path d="M6 2h9l4 4v16H6z" /><path d="M15 2v5h4M9 12h7M9 16h7M9 8h2" /></S>,
  sizechart: (p) => <S {...p}><rect x="3" y="4" width="18" height="16" rx="1" /><path d="M3 9h18M3 14h18M9 4v16M15 4v16" /></S>,
  estimate: (p) => <S {...p}><circle cx="12" cy="12" r="9" /><path d="M12 7v10M14.5 9.2c-.6-.7-1.5-1-2.5-1-1.4 0-2.5.8-2.5 2s1.1 1.8 2.5 2 2.5.6 2.5 1.9-1.1 2-2.5 2c-1 0-1.9-.4-2.5-1" /></S>,
  model3d: (p) => <S {...p}><path d="M12 2 3 7v10l9 5 9-5V7z" /><path d="M3 7l9 5 9-5M12 22V12" /></S>,
  arrow: (p) => <S {...p}><path d="M5 12h14M13 6l6 6-6 6" /></S>,
  plus: (p) => <S {...p}><path d="M12 5v14M5 12h14" /></S>,
  download: (p) => <S {...p}><path d="M12 3v12M7 11l5 5 5-5M4 20h16" /></S>,
  close: (p) => <S {...p}><path d="M6 6l12 12M18 6L6 18" /></S>,
  menu: (p) => <S {...p}><path d="M3 7h18M3 12h18M3 17h18" /></S>,
  upload: (p) => <S {...p}><path d="M12 20V8M7 12l5-5 5 5M4 4h16" /></S>,
  check: (p) => <S {...p}><path d="M4 12l5 5L20 6" /></S>,
};

export const TOOL_ICONS = {
  text2img: Icons.text2img, img2img: Icons.img2img, mockup: Icons.mockup, logo: Icons.logo,
  photoshoot: Icons.photoshoot, video: Icons.video, vector: Icons.vector, techpack: Icons.techpack,
  sizechart: Icons.sizechart, estimate: Icons.estimate, model3d: Icons.model3d,
};
