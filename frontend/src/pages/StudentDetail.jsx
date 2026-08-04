import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, User, BarChart2, BookOpen, Target, AlertCircle, Medal, Download } from 'lucide-react';
import apiClient from '../api/client';
import PerformanceLineChart from '../components/charts/PerformanceLineChart';
import SubjectRadarChart from '../components/charts/SubjectRadarChart';
import TopicBreakdownBar from '../components/charts/TopicBreakdownBar';

export default function StudentDetail() {
  const { id } = useParams();
  const [student, setStudent] = useState(null);
  const [results, setResults] = useState([]);
  const [performance, setPerformance] = useState([]);
  const [ranking, setRanking] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [studentRes, resultsRes, perfRes, rankRes] = await Promise.all([
          apiClient.get(`/students/${id}/`),
          apiClient.get(`/students/${id}/results`),
          apiClient.get(`/analytics/students/${id}/performance`),
          apiClient.get(`/analytics/students/${id}/ranking`).catch(() => ({ data: null })) // Fallback in case of error
        ]);
        
        setStudent(studentRes.data);
        setResults(Array.isArray(resultsRes.data) ? resultsRes.data : []);
        setPerformance(Array.isArray(perfRes.data) ? perfRes.data : []);
        setRanking(rankRes.data);
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
    );  // --- DATA PREPARATION FOR CHARTS ---

  // 1. Line Chart Data (Net Trend)
  const lineChartData = (performance || []).map((exam) => {
    const dataPoint = { name: exam?.exam_name || 'Sınav' };
    (exam?.subjects || []).forEach((sub) => {
      if (sub?.subject_name) {
        dataPoint[sub.subject_name] = sub.net ?? 0;
      }
    });
    return dataPoint;
  });

  const subjectNames = new Set();
  (performance || []).forEach((exam) => {
    (exam?.subjects || []).forEach((sub) => {
      if (sub?.subject_name) subjectNames.add(sub.subject_name);
    });
  });
  const subjects = Array.from(subjectNames);

  // 2. Radar Chart Data (Latest Subject Proficiency)
  const radarData = [];
  if (Array.isArray(performance) && performance.length > 0) {
    const latestExam = performance[performance.length - 1];
    (latestExam?.subjects || []).forEach((sub) => {
      if (sub?.subject_name) {
        radarData.push({
          subject: sub.subject_name,
          success_rate: sub.success_rate ?? 0,
          fullMark: 100,
        });
      }
    });
  }

  // 3. Topic Breakdown Bar Data (Weakest Topics overall)
  const topicStats = {};
  (results || []).forEach((r) => {
    if (!r?.measured) return; // Skip unmeasured outcomes
    const topicKey = r.topic_name || r.outcome_description || 'Genel';
    if (!topicStats[topicKey]) {
      topicStats[topicKey] = { correct: 0, total: 0 };
    }
    topicStats[topicKey].correct += r.correct || 0;
    topicStats[topicKey].total += r.total_questions || 0;
  });

  const topicData = Object.keys(topicStats)
    .map((topic) => {
      const stat = topicStats[topic];
      return {
        topic,
        success_rate: stat.total > 0 ? (stat.correct / stat.total) * 100 : 0,
      };
    })
    .sort((a, b) => a.success_rate - b.success_rate)
    .slice(0, 5);

  return (
    <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8 space-y-8">
      {/* Header & Breadcrumb */}
      <div>
        <Link
          to="/students"
          className="inline-flex items-center text-sm font-medium text-gray-500 hover:text-blue-600 mb-4 transition-colors"
        >
          <ArrowLeft className="w-4 h-4 mr-1" />
          Öğrenci Listesine Dön
        </Link>
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-blue-100 text-blue-700 rounded-full">
              <User className="w-8 h-8" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-gray-900">{student?.full_name || 'Öğrenci'}</h1>
              <p className="text-gray-500 font-medium mt-1">
                Sınıf: {student?.class_name || 'Belirtilmemiş'} • Kod: {student?.student_code || 'Belirtilmemiş'}
              </p>
            </div>
          </div>

          {/* Ranking Badge */}
          {ranking && ranking.total_in_institution > 0 && (
            <div className="flex items-center gap-4 bg-white border border-gray-200 rounded-xl p-4 shadow-sm">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-yellow-100 text-yellow-600 rounded-lg">
                  <Medal className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase">Kurum Derecesi</p>
                  <p className="text-lg font-bold text-gray-900">
                    {ranking.rank_in_institution}{' '}
                    <span className="text-sm font-normal text-gray-500">/ {ranking.total_in_institution}</span>
                  </p>
                </div>
              </div>
              <div className="w-px h-10 bg-gray-200 mx-2"></div>
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase">Sınıf Derecesi</p>
                <p className="text-lg font-bold text-gray-900">
                  {ranking.rank_in_class}{' '}
                  <span className="text-sm font-normal text-gray-500">/ {ranking.total_in_class}</span>
                </p>
              </div>
            </div>
          )}

          <button
            onClick={async () => {
              try {
                const response = await apiClient.get(`/students/${id}/export`, { responseType: 'blob' });
                const url = window.URL.createObjectURL(new Blob([response.data]));
                const link = document.createElement('a');
                link.href = url;
                link.setAttribute('download', `karne_${id}.xlsx`);
                document.body.appendChild(link);
                link.click();
                link.remove();
              } catch (err) {
                console.error('Excel indirme hatası:', err);
                alert('Karne indirilirken bir hata oluştu.');
              }
            }}
            className="inline-flex items-center justify-center px-4 py-2.5 border border-transparent text-sm font-medium rounded-lg shadow-sm text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
          >
            <Download className="w-4 h-4 mr-2" />
            Karne (Excel) İndir
          </button>
        </div>
      </div>

      {/* Grid Layout for Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Line Chart (Spans 2 columns) */}
        <div className="lg:col-span-2 bg-white rounded-2xl shadow-sm border border-gray-200 p-6 relative overflow-hidden flex flex-col">
          <div className="absolute top-0 right-0 p-32 bg-blue-50/50 rounded-full blur-3xl -mr-16 -mt-16 pointer-events-none"></div>
          <div className="flex items-center gap-2 mb-6">
            <BarChart2 className="w-6 h-6 text-blue-500" />
            <h2 className="text-xl font-bold text-gray-800">Net Gelişim Trendi</h2>
          </div>
          <div className="flex-1 min-h-[300px]">
            <PerformanceLineChart chartData={lineChartData} subjects={subjects} />
          </div>
        </div>

        {/* Right Column Stack */}
        <div className="flex flex-col gap-6">
          {/* Radar Chart */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 flex flex-col">
            <div className="flex items-center gap-2 mb-2">
              <Target className="w-5 h-5 text-indigo-500" />
              <h2 className="text-lg font-bold text-gray-800">Ders Yetkinlik Analizi</h2>
            </div>
            <p className="text-xs text-gray-500 mb-4">En son sınava göre başarı oranları</p>
            <div className="flex-1 min-h-[220px]">
              <SubjectRadarChart radarData={radarData} />
            </div>
          </div>

          {/* Topic Breakdown Bar */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 flex flex-col">
            <div className="flex items-center gap-2 mb-2">
              <AlertCircle className="w-5 h-5 text-red-500" />
              <h2 className="text-lg font-bold text-gray-800">En Zayıf Konular</h2>
            </div>
            <p className="text-xs text-gray-500 mb-4">Tüm sınavlar toplamındaki başarıya göre</p>
            <div className="flex-1 min-h-[180px]">
              <TopicBreakdownBar topicData={topicData} />
            </div>
          </div>
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
                <th scope="col" className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">
                  Sınav Adı
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">
                  Ders
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase max-w-xs">
                  Konu ve Kazanım
                </th>
                <th scope="col" className="px-3 py-3 text-center text-xs font-semibold text-gray-500 uppercase">
                  Soru
                </th>
                <th scope="col" className="px-3 py-3 text-center text-xs font-semibold text-green-600 uppercase">
                  D
                </th>
                <th scope="col" className="px-3 py-3 text-center text-xs font-semibold text-red-600 uppercase">
                  Y
                </th>
                <th scope="col" className="px-3 py-3 text-center text-xs font-semibold text-yellow-600 uppercase">
                  B
                </th>
                <th scope="col" className="px-4 py-3 text-center text-xs font-bold text-gray-700 uppercase">
                  Net
                </th>
                <th scope="col" className="px-6 py-3 text-right text-xs font-semibold text-gray-500 uppercase">
                  Başarı
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {results.length > 0 ? (
                results.map((r, idx) => {
                  const isMeasured = r?.measured !== false && r?.success_rate !== null && r?.success_rate !== undefined;
                  return (
                    <tr key={idx} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 font-medium">
                        {r?.exam_name || '—'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700 font-semibold">
                        {r?.subject_name || '—'}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600 max-w-xs truncate" title={r?.outcome_description}>
                        <span className="font-medium text-gray-800 block">{r?.topic_name || r?.outcome_description}</span>
                        {r?.topic_name && r?.outcome_description && (
                          <span className="text-xs text-gray-500">{r?.outcome_description}</span>
                        )}
                      </td>
                      <td className="px-3 py-4 whitespace-nowrap text-sm text-center text-gray-500">
                        {r?.total_questions ?? 0}
                      </td>
                      <td className="px-3 py-4 whitespace-nowrap text-sm text-center font-medium text-green-600">
                        {r?.correct ?? 0}
                      </td>
                      <td className="px-3 py-4 whitespace-nowrap text-sm text-center font-medium text-red-600">
                        {r?.wrong ?? 0}
                      </td>
                      <td className="px-3 py-4 whitespace-nowrap text-sm text-center font-medium text-yellow-600">
                        {r?.blank ?? 0}
                      </td>
                      <td className="px-4 py-4 whitespace-nowrap text-sm text-center font-bold text-gray-900">
                        {isMeasured && r?.net !== null && r?.net !== undefined ? r.net : '—'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right">
                        <span
                          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${
                            !isMeasured
                              ? 'bg-gray-100 text-gray-600 border-gray-200'
                              : (r?.success_rate ?? 0) >= 50
                              ? 'bg-green-50 text-green-700 border-green-200'
                              : 'bg-red-50 text-red-700 border-red-200'
                          }`}
                        >
                          {!isMeasured ? 'Ölçülmedi' : `%${Number(r.success_rate).toFixed(1)}`}
                        </span>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan="9" className="px-6 py-10 text-center text-sm text-gray-500">
                    Bu öğrenciye ait sonuç bulunamadı.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );e>
        </div>
      </div>
    </div>
  );
}
