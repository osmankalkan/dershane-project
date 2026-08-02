import { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { Users, FileText, AlertTriangle, TrendingDown } from 'lucide-react';
import apiClient from '../api/client';

export default function Dashboard() {
  const [stats, setStats] = useState({ students: 0, exams: 0 });
  const [weakTopics, setWeakTopics] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // MVP için veritabanındaki geçerli Kurum ID'si (UUID)
  const INSTITUTION_ID = 'b9c954c0-b532-4051-b830-639a98aecde1';

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        const [studentsRes, examsRes, weakTopicsRes] = await Promise.all([
          apiClient.get('/students/'),
          apiClient.get('/exams/'),
          apiClient.get(`/analytics/institutions/${INSTITUTION_ID}/weak-topics`)
        ]);

        setStats({
          students: studentsRes.data.length || 0,
          exams: examsRes.data.length || 0,
        });

        // Veriyi grafik için hazırla, uzun metinleri kısalt
        const formattedTopics = (weakTopicsRes.data || []).map(topic => ({
          ...topic,
          displayName: topic.topic_name.length > 25 ? topic.topic_name.substring(0, 25) + '...' : topic.topic_name,
          success_rate: Number(topic.success_rate)
        }));

        setWeakTopics(formattedTopics);
      } catch (err) {
        console.error("Dashboard veri hatası:", err);
        setError("Veriler yüklenirken bir hata oluştu.");
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto py-12 px-4 text-center">
        <div className="bg-red-50 text-red-800 p-6 rounded-xl border border-red-200">
          <p className="font-semibold">{error}</p>
        </div>
      </div>
    );
  }

  // Özel Tooltip bileşeni (Grafik üstüne gelince detay gösterir)
  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-white p-4 rounded-lg shadow-lg border border-gray-100 max-w-xs">
          <p className="font-bold text-gray-800 border-b pb-2 mb-2">{data.subject_name}</p>
          <p className="text-sm font-semibold text-gray-700">{data.topic_name}</p>
          <p className="text-xs text-gray-500 mt-1 italic">{data.outcome_description}</p>
          <div className="mt-3 pt-2 border-t flex justify-between items-center">
            <span className="text-sm text-gray-600">Başarı Oranı:</span>
            <span className={`font-bold ${data.success_rate < 40 ? 'text-red-600' : 'text-orange-500'}`}>
              %{data.success_rate}
            </span>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8 space-y-8">
      
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
          <TrendingDown className="w-8 h-8 text-indigo-600" />
          Kurum Paneli (Dashboard)
        </h1>
        <p className="mt-2 text-gray-500">Kurum genelindeki öğrenci performansı ve en zayıf kazanımların analizi.</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 flex items-center gap-6 transform hover:scale-[1.02] transition-transform">
          <div className="p-4 bg-blue-100 rounded-xl text-blue-600">
            <Users className="w-8 h-8" />
          </div>
          <div>
            <p className="text-sm font-medium text-gray-500 mb-1">Toplam Öğrenci</p>
            <h3 className="text-3xl font-bold text-gray-900">{stats.students}</h3>
          </div>
        </div>
        
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 flex items-center gap-6 transform hover:scale-[1.02] transition-transform">
          <div className="p-4 bg-green-100 rounded-xl text-green-600">
            <FileText className="w-8 h-8" />
          </div>
          <div>
            <p className="text-sm font-medium text-gray-500 mb-1">İşlenen Sınav</p>
            <h3 className="text-3xl font-bold text-gray-900">{stats.exams}</h3>
          </div>
        </div>
      </div>

      {/* Weak Topics Horizontal Bar Chart */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
        <div className="flex items-center gap-2 mb-8">
          <AlertTriangle className="w-6 h-6 text-red-500" />
          <h2 className="text-xl font-bold text-gray-800">Kurum Geneli En Zayıf Kazanımlar</h2>
        </div>
        
        <div className="h-[450px] w-full">
          {weakTopics.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={weakTopics}
                layout="vertical"
                margin={{ top: 5, right: 30, left: 40, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} stroke="#f3f4f6" />
                <XAxis 
                  type="number" 
                  domain={[0, 100]} 
                  tickFormatter={(val) => `%${val}`}
                  tick={{fill: '#6b7280', fontSize: 12}}
                />
                <YAxis 
                  type="category" 
                  dataKey="displayName" 
                  width={150} 
                  tick={{fill: '#4b5563', fontSize: 12, fontWeight: 500}} 
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip content={<CustomTooltip />} cursor={{fill: '#f9fafb'}} />
                <Bar 
                  dataKey="success_rate" 
                  radius={[0, 4, 4, 0]} 
                  barSize={24}
                  animationDuration={1500}
                >
                  {weakTopics.map((entry, index) => (
                    <Cell 
                      key={`cell-${index}`} 
                      fill={entry.success_rate < 30 ? '#ef4444' : entry.success_rate < 50 ? '#f97316' : '#eab308'} 
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-gray-400 gap-3">
              <AlertTriangle className="w-12 h-12 text-gray-300" />
              <p>Analiz edilecek yeterli sınav verisi bulunamadı.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
