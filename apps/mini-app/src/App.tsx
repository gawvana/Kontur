import { Routes, Route } from 'react-router-dom';
import Auth from './components/Auth';
import Layout from './components/Layout';
import Check from './pages/Check';
import Catalogs from './pages/Catalogs';
import Cases from './pages/Cases';
import Profile from './pages/Profile';

function App() {
  return (
    <Auth><Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Check />} />
        <Route path="catalogs" element={<Catalogs />} />
        <Route path="cases" element={<Cases />} />
        <Route path="profile" element={<Profile />} />
      </Route>
      <Route path="*" element={<p>Страница не найдена. Вернитесь к проверке.</p>} />
    </Routes></Auth>
  );
}

export default App;
