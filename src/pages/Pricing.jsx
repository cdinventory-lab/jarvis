import React, { useState } from 'react';
import { Nav, Footer } from '../components/SiteChrome.jsx';
import PricingTable from '../components/PricingTable.jsx';
import { Icons } from '../components/Icons.jsx';
import { useRouter } from '../router.jsx';

const FAQ = [
  ['Do I own what I generate?', 'Yes. Every mark, mockup and production file you generate on a paid plan comes with a commercial licence. You can print, sell and register the artwork.'],
  ['What is a credit?', 'Credits are the unit every generator draws from — mockups are 2, logos 3, 3D models 20. Your balance rolls over for the length of the plan.'],
  ['Can I use my own photos?', 'Yes. Upload a reference in the composer and pick “Image → Image”; JARVIS converts it into a one-colour print and presses it onto the garment.'],
  ['Are the files really print-ready?', 'Marks and vectors export as SVG or PNG at any size, one colour, so a screen printer or embroidery machine can use them directly. Tech packs and size charts export as CSV or print-ready A4.'],
  ['What if I run out of credits?', 'Nothing breaks. Top up from the Drop panel or move up a plan — unused credits are credited to the new balance.'],
  ['Do you offer refunds?', 'Cancel any time. Unused credit on a monthly plan is refundable in the first 14 days.'],
];

export default function Pricing() {
  const { navigate } = useRouter();
  const [open, setOpen] = useState(0);
  return (
    <div className="site">
      <Nav />
      <main>
        <section className="section pricing-head">
          <p className="eyebrow"><Icons.spark size={14} /> Plans &amp; credits</p>
          <h1 className="display">One balance.<br /><em>Eleven tools.</em></h1>
          <p className="section-lede">
            Pick a plan and start designing today. Every generation draws from the same credit balance —
            no seat fees, no per-asset surprises.
          </p>
          <div className="pricing-head-notes">
            <span className="mono-xs dim">Cancel anytime</span>
            <span className="mono-xs dim">Commercial licence</span>
            <span className="mono-xs dim">Credits roll over</span>
          </div>
        </section>

        <section className="section pricing-body">
          <PricingTable />
        </section>

        <section className="section faq">
          <div className="section-head">
            <p className="eyebrow">FAQ</p>
            <h2 className="display">Questions,<br /><em>answered.</em></h2>
          </div>
          <div className="faq-list">
            {FAQ.map(([q, a], i) => (
              <div key={q} className={`faq-item ${open === i ? 'is-open' : ''}`}>
                <button onClick={() => setOpen(open === i ? -1 : i)}>
                  <span>{q}</span>
                  <span className="faq-toggle">{open === i ? '−' : '+'}</span>
                </button>
                {open === i && <p>{a}</p>}
              </div>
            ))}
          </div>
        </section>

        <section className="cta">
          <div className="cta-inner">
            <p className="eyebrow">Start now</p>
            <h2 className="display">Make the first<br /><em>mockup free.</em></h2>
            <p className="section-lede">New accounts start with 20 credits — enough for a logo and two mockups.</p>
            <div className="cta-actions">
              <button className="btn btn-solid lg" onClick={() => navigate('/studio')}>Open the studio <Icons.arrow /></button>
              <a className="btn btn-line lg" href="/#how">How it works</a>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
}
