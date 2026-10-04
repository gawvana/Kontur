import { useEffect } from 'react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import Icon from './Icon';
export default function Layout() {
  const location = useLocation(); const navigate = useNavigate();
  useEffect(() => {
    const back = window.Telegram?.WebApp.BackButton;
    if (!back) return;
    const handle = () => navigate(-1);
    if (location.pathname === '/') back.hide(); else back.show();
    back.onClick(handle);
    return () => back.offClick(handle);
  }, [location.pathname, navigate]);
  const items = [{ path: '/', label: 'Проверка', icon: 'search' }, { path: '/catalogs', label: 'Каталоги', icon: 'folder' }, { path: '/cases', label: 'Обращения', icon: 'cases' }, { path: '/profile', label: 'Профиль', icon: 'user' }];
  return <div className="app-shell"><header className="topbar"><h1>Контур</h1></header><main className="page"><Outlet /></main><nav className="dock" aria-label="Основные разделы">{items.map(item => <Link key={item.path} to={item.path} aria-current={location.pathname === item.path ? 'page' : undefined}><Icon name={item.icon} active={location.pathname === item.path} /><span>{item.label}</span></Link>)}</nav></div>;
}
