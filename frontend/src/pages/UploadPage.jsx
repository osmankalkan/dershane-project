import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { UploadCloud, CheckCircle, AlertCircle, FileText, Loader2 } from 'lucide-react';
import apiClient from '../api/client';

export default function UploadPage() {
  const [uploadStatus, setUploadStatus] = useState(null); // 'uploading', 'success', 'error', 'duplicate'
  const [message, setMessage] = useState('');
  
  const onDrop = useCallback(async (acceptedFiles) => {
    const file = acceptedFiles[0];
    if (!file) return;

    setUploadStatus('uploading');
    setMessage('Belge yükleniyor ve analiz ediliyor...');

    const formData = new FormData();
    formData.append('file', file);
    // Hardcoded institution_id ve date MVP için
    formData.append('institution_id', 'inst-001');
    formData.append('exam_date', new Date().toISOString().split('T')[0]);

    try {
      // Axios request with multipart form
      const res = await apiClient.post('/upload/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      if (res.data.status === 'DUPLICATE') {
        setUploadStatus('duplicate');
        setMessage('Bu PDF belgesi daha önce sisteme yüklenmiş!');
      } else {
        setUploadStatus('success');
        setMessage('PDF başarıyla işlendi ve veritabanına kaydedildi!');
      }
    } catch (err) {
      setUploadStatus('error');
      setMessage(err.response?.data?.detail || 'Belge yüklenirken beklenmeyen bir hata oluştu.');
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    multiple: false
  });

  return (
    <div className="max-w-4xl mx-auto py-12 px-4 sm:px-6 lg:px-8">
      <div className="text-center mb-10">
        <h1 className="text-4xl font-extrabold text-gray-900 tracking-tight mb-2">
          Sınav Sonucu Yükle
        </h1>
        <p className="text-lg text-gray-500">
          PDF formatındaki öğrenci sınav sonuç belgelerini buraya sürükleyip bırakabilirsiniz.
        </p>
      </div>

      <div 
        {...getRootProps()} 
        className={`relative group flex flex-col items-center justify-center p-16 border-3 border-dashed rounded-2xl transition-all duration-300 ease-in-out bg-white overflow-hidden cursor-pointer shadow-sm
          ${isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50 hover:shadow-md'}`}
      >
        <input {...getInputProps()} />
        
        {/* Background decorative glow on hover */}
        <div className="absolute inset-0 bg-gradient-to-br from-blue-50 to-indigo-50 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />

        <div className="z-10 flex flex-col items-center">
          <div className={`p-4 rounded-full mb-6 transition-transform duration-300 ${isDragActive ? 'bg-blue-100 scale-110' : 'bg-gray-100 group-hover:scale-110 group-hover:bg-blue-50'}`}>
            <UploadCloud className={`w-12 h-12 ${isDragActive ? 'text-blue-600' : 'text-gray-400 group-hover:text-blue-500'}`} />
          </div>
          
          <h3 className="text-xl font-bold text-gray-800 mb-2">
            {isDragActive ? 'Dosyayı buraya bırakın...' : 'PDF belgesini sürükleyin veya seçin'}
          </h3>
          <p className="text-sm text-gray-500 font-medium">Sadece .pdf formatındaki dosyalar desteklenir</p>
        </div>
      </div>

      {/* Status Indicators */}
      {uploadStatus && (
        <div className={`mt-8 p-6 rounded-xl border flex items-start space-x-4 animate-in fade-in slide-in-from-bottom-4 duration-500 shadow-sm
          ${uploadStatus === 'uploading' ? 'bg-blue-50 border-blue-200' : ''}
          ${uploadStatus === 'success' ? 'bg-green-50 border-green-200' : ''}
          ${uploadStatus === 'error' ? 'bg-red-50 border-red-200' : ''}
          ${uploadStatus === 'duplicate' ? 'bg-orange-50 border-orange-200' : ''}
        `}>
          
          <div className="mt-1">
            {uploadStatus === 'uploading' && <Loader2 className="w-6 h-6 text-blue-500 animate-spin" />}
            {uploadStatus === 'success' && <CheckCircle className="w-6 h-6 text-green-500" />}
            {uploadStatus === 'error' && <AlertCircle className="w-6 h-6 text-red-500" />}
            {uploadStatus === 'duplicate' && <FileText className="w-6 h-6 text-orange-500" />}
          </div>
          
          <div>
            <h4 className={`text-lg font-semibold 
              ${uploadStatus === 'uploading' ? 'text-blue-800' : ''}
              ${uploadStatus === 'success' ? 'text-green-800' : ''}
              ${uploadStatus === 'error' ? 'text-red-800' : ''}
              ${uploadStatus === 'duplicate' ? 'text-orange-800' : ''}
            `}>
              {uploadStatus === 'uploading' && 'İşlem Devam Ediyor'}
              {uploadStatus === 'success' && 'Yükleme Başarılı'}
              {uploadStatus === 'error' && 'Yükleme Başarısız'}
              {uploadStatus === 'duplicate' && 'Kopya Dosya'}
            </h4>
            <p className={`mt-1 font-medium
              ${uploadStatus === 'uploading' ? 'text-blue-600' : ''}
              ${uploadStatus === 'success' ? 'text-green-600' : ''}
              ${uploadStatus === 'error' ? 'text-red-600' : ''}
              ${uploadStatus === 'duplicate' ? 'text-orange-600' : ''}
            `}>
              {message}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
