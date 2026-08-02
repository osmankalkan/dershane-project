import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import UploadPage from './pages/UploadPage';
import StudentsList from './pages/StudentsList';
import StudentDetail from './pages/StudentDetail';
import Dashboard from './pages/Dashboard';
import ExamManagement from './pages/ExamManagement';

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/students" element={<StudentsList />} />
          <Route path="/students/:id" element={<StudentDetail />} />
          <Route path="/exams" element={<ExamManagement />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;
