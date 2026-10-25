import React, { useState } from 'react';
import { useRouter } from '../router.jsx';
import { useStudio } from '../store.jsx';
import { TOOLS, TOOL_ORDER } from '../lib/engine.js';
import { Icons } from './Icons.jsx';

export const PLANS = [
  {
    id: 'Starter', name: 'Starter', price: 9, annual: 7.25, credits: 75, yearCredits: 900,
    blurb: 'For exploring AI fashion design.',
    features: ['75 credits / month', 'All 11 tools', 'SVG + PNG export', 'Commercial licence'],
  },
  {
    id: 'Creator', name: 'Creator', price: 19, annual: 15.25, credits: 225, yearCredits: 2700,
    blurb: 'For creators building a first drop.', popular: true,
    features: ['225 credits / month', 'All 11 tools', 'Tech pack + size chart export', 'Photoshoot video', 'Priority queue'],
  },
  {
    id: 'Professional', name: 'Professional', price: 49, annual: 39.25, credits: 810, yearCredits: 9720,
    blurb: 'For labels shipping collections.',
    features: ['810 credits / month', 'Everything in Creator', '3D models (.glb)', 'Batch variations', 'Shared team projects'],
  },
];

const COSTS = TOOL_ORDER.filter((t) => TOOLS[t]).map((t) => [TOOLS[t].label, TOOLS[t].cost]);

export default function PricingTable({ compact = false }) {
  const [annual, setAnnual] = useState(true);
  const [chosen, setChosen] = useState('Creator');
  const { dispatch } = useStudio();
  const { navigate } = useRouter();

  const pick = (plan) => {
    setChosen(plan.id);
    dispatch({ type: 'plan', payload: plan.id, credits: annual ? Math.round(plan.yearCredits / 12) : plan.credits });
    navigate('/studio');
  };

  return (
    <div className={`pricing ${compact ? 'is-compact' : ''}`}>
      <div className="pricing-toggle">
        <button className={!annual ? 'is-active' : ''} onClick={() => setAnnual(false)}>Monthly</button>
        <button className={annual ? 'is-active' : ''} onClick={() => setAnnual(true)}>Annual <em>save 20%</em></button>
      </div>

      <div className="plan-grid">
        {PLANS.map((plan) => {
          const price = annual ? plan.annual : plan.price;
          const credits = annual ? plan.yearCredits : plan.credits;
          return (
            <article key={plan.id} className={`plan ${plan.popular ? 'is-popular' : ''} ${chosen === plan.id ? 'is-chosen' : ''}`}>
              {plan.popular && <span className="plan-flag mono-xs">MOST POPULAR</span>}
              <header>
                <h3>{plan.name}</h3>
                <p className="plan-blurb">{plan.blurb}</p>
              </header>
              <div className="plan-price">
                <span className="currency">$</span>
                <span className="amount">{price.toFixed(2)}</span>
                <span className="per">/month</span>
              </div>
              <p className="mono-xs dim">
                {annual ? `billed annually · $${Math.round(price * 12)} / year` : 'billed monthly · cancel anytime'}
              </p>
              <div className="plan-credits">
                <strong>{credits.toLocaleString()}</strong>
                <span className="mono-xs">credits / {annual ? 'year' : 'month'}</span>
              </div>
              <ul className="plan-features">
                {plan.features.map((f) => <li key={f}><Icons.check size={14} />{f}</li>)}
              </ul>
              <button className={`btn ${plan.popular ? 'btn-solid' : 'btn-line'} wide`} onClick={() => pick(plan)}>
                Choose {plan.name} <Icons.arrow size={15} />
              </button>
              <p className="mono-xs dim plan-example">
                ≈ {Math.floor(credits / TOOLS.mockup.cost)} mockups · {Math.floor(credits / TOOLS.logo.cost)} logos
                · {Math.floor(credits / TOOLS.model3d.cost)} 3D models
              </p>
            </article>
          );
        })}
      </div>

      {!compact && (
        <div className="costs">
          <div className="costs-head">
            <p className="mono-xs dim">WHAT EACH GENERATION COSTS</p>
            <p className="mono-xs dim">credits</p>
          </div>
          <div className="costs-grid">
            {COSTS.map(([label, cost]) => (
              <div key={label} className="cost-row">
                <span>{label}</span>
                <span className="dots" aria-hidden="true" />
                <em>{cost}</em>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
