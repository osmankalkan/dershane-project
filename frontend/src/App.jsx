import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import UploadPage from './pages/UploadPage';
import StudentsList from './pages/StudentsList';
import StudentDetail from './pages/StudentDetail';

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<UploadPage />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/students" element={<StudentsList />} />
          <Route path="/students/:id" element={<StudentDetail />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;
