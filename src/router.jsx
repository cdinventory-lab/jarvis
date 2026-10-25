import React, { createContext, useContext, useEffect, useState } from 'react';

const RouterCtx = createContext({ path: '/', navigate: () => {} });

export function RouterProvider({ children }) {
  const [path, setPath] = useState(window.location.pathname);
  useEffect(() => {
    const onPop = () => setPath(window.location.pathname);
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, []);
  const navigate = (to, opts = {}) => {
    if (to === path) return;
    window.history.pushState({}, '', to);
    setPath(to);
    if (!opts.keepScroll) { try { window.scrollTo({ top: 0 }); } catch {} }
  };
  return <RouterCtx.Provider value={{ path, navigate }}>{children}</RouterCtx.Provider>;
}

export const useRouter = () => useContext(RouterCtx);

export function Link({ to, children, className, onClick, ...rest }) {
  const { navigate } = useRouter();
  return (
    <a href={to} className={className} {...rest}
      onClick={(e) => { e.preventDefault(); onClick?.(); navigate(to); }}>
      {children}
    </a>
  );
}
