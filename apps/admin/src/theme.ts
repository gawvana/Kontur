const applyTheme = () => {
  const chosen = localStorage.getItem('kontur-theme');
  const telegram = (window as Window & { Telegram?: { WebApp?: { colorScheme?: string } } }).Telegram?.WebApp?.colorScheme;
  const dark = chosen === 'dark' || (chosen !== 'light' && (telegram ? telegram === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches));
  document.documentElement.classList.toggle('dark', dark);
};
applyTheme();
window.addEventListener('kontur-theme', applyTheme);
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', applyTheme);
