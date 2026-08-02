import { useState, useEffect } from 'react';
import { Trash2, AlertTriangle, FileText, Loader2 } from 'lucide-react';

export default function ExamManagement() {
  const [exams, setExams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState(null);

  const fetchExams = async () => {
    try {
      const res = await fetch('/api/v1/exams');
      if (res.ok) {
        const data = await res.json();
        setExams(data);
      }
    } catch (err) {
      console.error('Failed to fetch exams:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchExams();
  }, []);

  const handleDelete = async (examId, examName) => {
    if (!window.confirm(`⚠️ DİKKAT!\n\n"${examName}" sınavını silmek üzeresiniz.\nBu işlem bu sınava ait TÜM öğrenci sonuçlarını kalıcı olarak silecektir.\n\nOnaylıyor musunuz?`)) {
      return;
    }

    setDeletingId(examId);
    try {
      const res = await fetch(`/api/v1/exams/${examId}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        // Remove from UI
        setExams(exams.filter(e => e.id !== examId));
        alert('Sınav ve tüm sonuçları başarıyla silindi.');
      } else {
        alert('Sınav silinirken bir hata oluştu.');
      }
    } catch (err) {
      console.error('Error deleting exam:', err);
      alert('Sistem hatası!');
    } finally {
      setDeletingId(null);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="sm:flex sm:items-center sm:justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <span className="text-red-500">⚙️</span> Sınav Yönetimi
          </h1>
          <p className="mt-2 text-sm text-gray-700">
            Sisteme yüklenen tüm deneme sınavlarını buradan yönetebilir, hatalı veya eski verileri silebilirsiniz.
          </p>
        </div>
      </div>

      <div className="bg-red-50 border-l-4 border-red-500 p-4 mb-6 rounded-r-lg">
        <div className="flex">
          <div className="flex-shrink-0">
            <AlertTriangle className="h-5 w-5 text-red-500" />
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800">Kritik Uyarı</h3>
            <div className="mt-2 text-sm text-red-700">
              <p>Bir sınavı sildiğinizde, o sınava ait tüm öğrencilerin test sonuçları, başarı oranları ve genel sıralamaları <b>kalıcı olarak</b> sistemden temizlenir. Bu işlem geri alınamaz.</p>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white shadow-sm ring-1 ring-gray-200 rounded-xl overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50/50">
            <tr>
              <th scope="col" className="py-4 pl-6 pr-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Sınav Adı</th>
              <th scope="col" className="px-3 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Sınav Tarihi</th>
              <th scope="col" className="px-3 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Sisteme Yüklenme</th>
              <th scope="col" className="relative py-4 pl-3 pr-6 text-right font-medium">İşlem</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 bg-white">
            {exams.length > 0 ? (
              exams.map((exam) => (
                <tr key={exam.id} className="hover:bg-gray-50 transition-colors">
                  <td className="whitespace-nowrap py-4 pl-6 pr-3 text-sm font-medium text-gray-900 flex items-center gap-2">
                    <FileText className="w-5 h-5 text-blue-500" />
                    {exam.name}
                  </td>
                  <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                    {new Date(exam.exam_date).toLocaleDateString('tr-TR')}
                  </td>
                  <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                    {new Date(exam.created_at).toLocaleString('tr-TR')}
                  </td>
                  <td className="whitespace-nowrap py-4 pl-3 pr-6 text-right text-sm font-medium">
                    <button
                      onClick={() => handleDelete(exam.id, exam.name)}
                      disabled={deletingId === exam.id}
                      className="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded text-red-700 bg-red-100 hover:bg-red-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition-colors disabled:opacity-50"
                    >
                      {deletingId === exam.id ? (
                        <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                      ) : (
                        <Trash2 className="w-4 h-4 mr-1" />
                      )}
                      Kalıcı Olarak Sil
                    </button>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan="4" className="py-10 text-center text-gray-500">
                  Sistemde henüz kayıtlı sınav bulunmuyor.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
