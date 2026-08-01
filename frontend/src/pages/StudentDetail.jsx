import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, User, BarChart2, BookOpen } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import apiClient from '../api/client';

export default function StudentDetail() {
  const { id } = useParams();
  const [student, setStudent] = useState(null);
  const [results, setResults] = useState([]);
  const [performance, setPerformance] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [studentRes, resultsRes, perfRes] = await Promise.all([
          apiClient.get(`/students/${id}`),
          apiClient.get(`/students/${id}/results`),
          apiClient.get(`/analytics/students/${id}/performance`)
        ]);
        
        setStudent(studentRes.data);
        setResults(Array.isArray(resultsRes.data) ? resultsRes.data : []);
        setPerformance(Array.isArray(perfRes.data) ? perfRes.data : []);
      } catch (err) {
        console.error("API Hatası:", err);
        setError("Öğrenci verileri yüklenirken bir hata oluştu.");
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, [id]);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto py-12 px-4 text-center">
        <div className="bg-red-50 text-red-800 p-6 rounded-xl border border-red-200">
          <h2 className="text-2xl font-bold mb-2">Hata</h2>
          <p>{error}</p>
          <Link to="/students" className="mt-4 inline-block text-blue-600 hover:underline">Listeye Dön</Link>
        </div>
      </div>
    );
  }

  // Grafik verisini hazırla
  const chartData = performance.map(exam => {
    const dataPoint = { name: exam.exam_name };
    exam.subjects.forEach(sub => {
      dataPoint[sub.subject_name] = sub.net;
    });
    return dataPoint;
  });
  
  const subjectNames = new Set();
  performance.forEach(exam => {
    exam.subjects.forEach(sub => subjectNames.add(sub.subject_name));
  });
  const subjects = Array.from(subjectNames);
  const colors = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#14b8a6"];

  return (
    <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8 space-y-8">
      {/* Header & Breadcrumb */}
      <div>
        <Link to="/students" className="inline-flex items-center text-sm font-medium text-gray-500 hover:text-blue-600 mb-4 transition-colors">
          <ArrowLeft className="w-4 h-4 mr-1" />
          Öğrenci Listesine Dön
        </Link>
        <div className="flex items-center gap-4">
          <div className="p-3 bg-blue-100 text-blue-700 rounded-full">
            <User className="w-8 h-8" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">{student?.full_name}</h1>
            <p className="text-gray-500 font-medium mt-1">Sınıf: {student?.class_name} • Kod: {student?.student_code || 'Belirtilmemiş'}</p>
          </div>
        </div>
      </div>

      {/* Analytics Chart */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 relative overflow-hidden">
        <div className="absolute top-0 right-0 p-32 bg-blue-50/50 rounded-full blur-3xl -mr-16 -mt-16 pointer-events-none"></div>
        <div className="flex items-center gap-2 mb-6">
          <BarChart2 className="w-6 h-6 text-blue-500" />
          <h2 className="text-xl font-bold text-gray-800">Net Gelişim Trendi</h2>
        </div>
        
        <div className="h-80 w-full">
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{fill: '#6b7280', fontSize: 12}} dy={10} />
                <YAxis axisLine={false} tickLine={false} tick={{fill: '#6b7280', fontSize: 12}} dx={-10} />
                <Tooltip 
                  contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)' }}
                  cursor={{ stroke: '#e5e7eb', strokeWidth: 2, strokeDasharray: '3 3' }}
                />
                <Legend iconType="circle" wrapperStyle={{ paddingTop: '20px' }} />
                {subjects.map((sub, i) => (
                  <Line 
                    key={sub} 
                    type="monotone" 
                    dataKey={sub} 
                    stroke={colors[i % colors.length]} 
                    strokeWidth={3}
                    dot={{ r: 4, strokeWidth: 2 }}
                    activeDot={{ r: 6, strokeWidth: 0 }} 
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-gray-400">
              Grafik için yeterli sınav verisi bulunmuyor.
            </div>
          )}
        </div>
      </div>

      {/* Detailed Results Table */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="p-6 border-b border-gray-200 flex items-center gap-2 bg-gray-50/30">
          <BookOpen className="w-6 h-6 text-indigo-500" />
          <h2 className="text-xl font-bold text-gray-800">Kazanım Detaylı Sınav Sonuçları</h2>
        </div>
        
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th scope="col" className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Sınav Adı</th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Ders</th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase max-w-xs">Konu ve Kazanım</th>
                <th scope="col" className="px-3 py-3 text-center text-xs font-semibold text-gray-500 uppercase">Soru</th>
                <th scope="col" className="px-3 py-3 text-center text-xs font-semibold text-green-600 uppercase">D</th>
                <th scope="col" className="px-3 py-3 text-center text-xs font-semibold text-red-600 uppercase">Y</th>
                <th scope="col" className="px-3 py-3 text-center text-xs font-semibold text-yellow-600 uppercase">B</th>
                <th scope="col" className="px-4 py-3 text-center text-xs font-bold text-gray-700 uppercase">Net</th>
                <th scope="col" className="px-6 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Başarı</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {results.length > 0 ? (
                results.map((r, idx) => (
                  <tr key={idx} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 font-medium">{r.exam_name}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700 font-semibold">{r.subject_name}</td>
                    <td className="px-6 py-4 text-sm text-gray-600 max-w-xs truncate" title={r.outcome_description}>
                      <span className="font-medium text-gray-800 block">{r.topic_name}</span>
                      <span className="text-xs text-gray-500">{r.outcome_description}</span>
                    </td>
                    <td className="px-3 py-4 whitespace-nowrap text-sm text-center text-gray-500">{r.total_questions}</td>
                    <td className="px-3 py-4 whitespace-nowrap text-sm text-center font-medium text-green-600">{r.correct}</td>
                    <td className="px-3 py-4 whitespace-nowrap text-sm text-center font-medium text-red-600">{r.wrong}</td>
                    <td className="px-3 py-4 whitespace-nowrap text-sm text-center font-medium text-yellow-600">{r.blank}</td>
                    <td className="px-4 py-4 whitespace-nowrap text-sm text-center font-bold text-gray-900">{r.net}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border
                        ${r.success_rate >= 50 ? 'bg-green-50 text-green-700 border-green-200' : 'bg-red-50 text-red-700 border-red-200'}
                      `}>
                        %{r.success_rate.toFixed(1)}
                      </span>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="9" className="px-6 py-10 text-center text-sm text-gray-500">Bu öğrenciye ait sonuç bulunamadı.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
