import React, { useEffect } from 'react';
import { useRouter } from './router.jsx';
import Landing from './pages/Landing.jsx';
import Studio from './pages/Studio.jsx';
import Pricing from './pages/Pricing.jsx';

export default function App() {
  const { path } = useRouter();

  useEffect(() => {
    document.body.dataset.route = path.startsWith('/studio') ? 'studio' : 'site';
  }, [path]);

  if (path.startsWith('/studio')) return <Studio />;
  if (path.startsWith('/pricing')) return <Pricing />;
  return <Landing />;
}
