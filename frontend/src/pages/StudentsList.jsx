import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Users, ChevronRight, Search, Filter, Download } from 'lucide-react';
import apiClient from '../api/client';

export default function StudentsList() {
  const [students, setStudents] = useState([]);
  const [classes, setClasses] = useState([]);
  const [selectedClassId, setSelectedClassId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  // Sınıfları çek
  useEffect(() => {
    const fetchClasses = async () => {
      try {
        const res = await apiClient.get('/classes/');
        setClasses(res.data);
      } catch (err) {
        console.error("Sınıflar yüklenemedi:", err);
      }
    };
    fetchClasses();
  }, []);

  // Öğrencileri çek (Sınıf filtresi değiştiğinde tekrar çalışır)
  useEffect(() => {
    const fetchStudents = async () => {
      setLoading(true);
      try {
        const url = selectedClassId ? `/students/?class_id=${selectedClassId}` : '/students/';
        const res = await apiClient.get(url);
        setStudents(res.data);
      } catch (err) {
        console.error("API Hatası:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchStudents();
  }, [selectedClassId]);

  const handleExport = async () => {
    setExporting(true);
    try {
      const response = await apiClient.get('/students/export', { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'ogrenciler.xlsx');
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      console.error("Excel indirme hatası:", err);
      alert("Excel dosyası indirilirken bir hata oluştu.");
    } finally {
      setExporting(false);
    }
  };

  const filteredStudents = students.filter(s => 
    s.full_name.toLowerCase().includes(searchTerm.toLowerCase()) || 
    (s.student_code && s.student_code.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  return (
    <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
      <div className="mb-8 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
            <Users className="w-8 h-8 text-blue-600" />
            Öğrenciler
          </h1>
          <p className="mt-1 text-sm text-gray-500">Sisteme kayıtlı tüm öğrencilerin listesi ve analizleri</p>
        </div>
        
        <div className="flex flex-col sm:flex-row gap-3 w-full sm:w-auto">
          <div className="relative w-full sm:w-64">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Search className="h-5 w-5 text-gray-400" />
            </div>
            <input
              type="text"
              className="block w-full pl-10 pr-3 py-2.5 border border-gray-300 rounded-lg leading-5 bg-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors sm:text-sm"
              placeholder="İsim veya Kod ile ara..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          
          <button
            onClick={handleExport}
            disabled={exporting}
            className="inline-flex items-center justify-center px-4 py-2.5 border border-transparent text-sm font-medium rounded-lg shadow-sm text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Download className="w-4 h-4 mr-2" />
            {exporting ? 'İndiriliyor...' : "Excel'e Aktar"}
          </button>
        </div>
      </div>

      {/* Sınıf Filtreleme Sekmeleri */}
      <div className="mb-6 flex items-center gap-2 overflow-x-auto pb-2 scrollbar-hide">
        <Filter className="w-5 h-5 text-gray-400 mr-2 shrink-0" />
        <button
          onClick={() => setSelectedClassId(null)}
          className={`shrink-0 px-4 py-2 text-sm font-medium rounded-full transition-colors ${
            selectedClassId === null 
              ? 'bg-blue-600 text-white shadow-sm' 
              : 'bg-white text-gray-600 hover:bg-gray-50 border border-gray-200'
          }`}
        >
          Tüm Sınıflar
        </button>
        {classes.map(cls => (
          <button
            key={cls.id}
            onClick={() => setSelectedClassId(cls.id)}
            className={`shrink-0 px-4 py-2 text-sm font-medium rounded-full transition-colors ${
              selectedClassId === cls.id 
                ? 'bg-blue-600 text-white shadow-sm' 
                : 'bg-white text-gray-600 hover:bg-gray-50 border border-gray-200'
            }`}
          >
            {cls.name}
          </button>
        ))}
      </div>

      <div className="bg-white shadow-sm ring-1 ring-gray-200 rounded-xl overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50/50">
            <tr>
              <th scope="col" className="py-4 pl-6 pr-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Derece</th>
              <th scope="col" className="px-3 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Ad Soyad</th>
              <th scope="col" className="px-3 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Sınıf</th>
              <th scope="col" className="px-3 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Ortalama Net</th>
              <th scope="col" className="relative py-4 pl-3 pr-6 text-right font-medium">İşlem</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 bg-white">
            {loading ? (
              <tr>
                <td colSpan="5" className="py-10 text-center text-gray-500">Öğrenciler yükleniyor...</td>
              </tr>
            ) : filteredStudents.length > 0 ? (
              filteredStudents.map((student) => (
                <tr key={student.id} className="hover:bg-blue-50/50 transition-colors group cursor-default">
                  <td className="whitespace-nowrap py-4 pl-6 pr-3 text-sm font-medium text-gray-900">
                    {student.rank === 1 && <span className="text-xl" title="1. Sıra">🥇</span>}
                    {student.rank === 2 && <span className="text-xl" title="2. Sıra">🥈</span>}
                    {student.rank === 3 && <span className="text-xl" title="3. Sıra">🥉</span>}
                    {student.rank > 3 && <span className="text-gray-500 font-bold ml-1">{student.rank}.</span>}
                  </td>
                  <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-700 font-semibold">
                    <div className="flex flex-col">
                      <span>{student.full_name}</span>
                      <span className="text-xs text-gray-400">{student.student_code || '-'}</span>
                    </div>
                  </td>
                  <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                      {student.class_name}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                    <span className={`inline-flex items-center px-2.5 py-1 rounded-md text-xs font-bold ${
                      student.avg_net > 0 
                        ? 'bg-green-100 text-green-800 border border-green-200' 
                        : 'bg-gray-100 text-gray-600 border border-gray-200'
                    }`}>
                      {student.avg_net} Net
                    </span>
                  </td>
                  <td className="whitespace-nowrap py-4 pl-3 pr-6 text-right text-sm font-medium">
                    <Link 
                      to={`/students/${student.id}`} 
                      className="inline-flex items-center text-blue-600 hover:text-blue-900 font-semibold group-hover:underline"
                    >
                      İncele <ChevronRight className="w-4 h-4 ml-1" />
                    </Link>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan="5" className="py-10 text-center text-gray-500">Eşleşen öğrenci bulunamadı.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
