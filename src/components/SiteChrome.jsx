import React, { useEffect, useState } from 'react';
import { Link, useRouter } from '../router.jsx';
import { useStudio } from '../store.jsx';
import { Icons } from './Icons.jsx';

export function Wordmark({ light = false }) {
  return (
    <span className={`wordmark ${light ? 'on-dark' : ''}`}>
      <span className="wordmark-glyph" aria-hidden="true">
        <svg viewBox="0 0 24 24"><path d="M3 21 12 2l9 19h-4.6L12 9.6 7.6 21z" fill="currentColor" /></svg>
      </span>
      <span className="wordmark-text">JARVIS</span>
    </span>
  );
}

const LINKS = [
  ['How it works', '#how'],
  ['Tools', '#tools'],
  ['Gallery', '#gallery'],
  ['Pricing', '#pricing'],
];

export function Nav() {
  const { navigate } = useRouter();
  const { state } = useStudio();
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const go = (e, href) => {
    e.preventDefault();
    setOpen(false);
    if (href.startsWith('#')) {
      const el = document.querySelector(href);
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      else navigate('/');
    } else navigate(href);
  };

  return (
    <header className={`nav ${scrolled ? 'is-scrolled' : ''}`}>
      <div className="nav-inner">
        <Link to="/" className="nav-brand" aria-label="JARVIS home"><Wordmark /></Link>
        <nav className="nav-links">
          {LINKS.map(([label, href]) => (
            <a key={href} href={href} onClick={(e) => go(e, href)}>{label}</a>
          ))}
        </nav>
        <div className="nav-actions">
          <span className="nav-credits mono-xs">{state.credits} credits</span>
          <button className="btn btn-line" onClick={() => navigate('/pricing')}>Plans</button>
          <button className="btn btn-solid" onClick={() => navigate('/studio')}>
            Open studio <Icons.arrow size={15} />
          </button>
          <button className="nav-burger" aria-label="Menu" onClick={() => setOpen((o) => !o)}>
            {open ? <Icons.close /> : <Icons.menu />}
          </button>
        </div>
      </div>
      {open && (
        <div className="nav-drawer">
          {LINKS.map(([label, href]) => (
            <a key={href} href={href} onClick={(e) => go(e, href)}>{label}</a>
          ))}
          <a href="/pricing" onClick={(e) => go(e, '/pricing')}>Plans &amp; credits</a>
          <a href="/studio" onClick={(e) => go(e, '/studio')}>Open studio</a>
        </div>
      )}
    </header>
  );
}

export function Footer() {
  const { navigate } = useRouter();
  return (
    <footer className="footer">
      <div className="footer-top">
        <div className="footer-brand">
          <Wordmark light />
          <p>An AI studio for clothing brands. Marks, mockups, photoshoots and production files — one conversation, one colour.</p>
        </div>
        <div className="footer-cols">
          <div>
            <p className="mono-xs dim">PRODUCT</p>
            <a href="/studio" onClick={(e) => { e.preventDefault(); navigate('/studio'); }}>Studio</a>
            <a href="#tools" onClick={(e) => { e.preventDefault(); navigate('/'); }}>Tools</a>
            <a href="/pricing" onClick={(e) => { e.preventDefault(); navigate('/pricing'); }}>Pricing</a>
          </div>
          <div>
            <p className="mono-xs dim">COMPANY</p>
            <a href="#how" onClick={(e) => { e.preventDefault(); navigate('/'); }}>How it works</a>
            <a href="#about" onClick={(e) => { e.preventDefault(); navigate('/'); }}>About</a>
            <a href="mailto:studio@jarvis.design">Contact</a>
          </div>
          <div>
            <p className="mono-xs dim">LEGAL</p>
            <a href="#">Terms</a>
            <a href="#">Privacy</a>
            <a href="#">Licensing</a>
          </div>
        </div>
      </div>
      <div className="footer-bottom">
        <span className="mono-xs dim">© {new Date().getFullYear()} JARVIS Studio — all artwork generated monochrome.</span>
        <span className="mono-xs dim">Kigali · Berlin · online</span>
      </div>
    </footer>
  );
}
