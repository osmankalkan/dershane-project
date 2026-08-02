import { Link, useLocation } from 'react-router-dom';
import { Upload, Users, GraduationCap, LayoutDashboard } from 'lucide-react';

export default function Layout({ children }) {
  const location = useLocation();
  
  const isActive = (path) => {
    return location.pathname.startsWith(path);
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Top Navigation Bar */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              {/* Logo */}
              <div className="flex-shrink-0 flex items-center gap-2">
                <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white">
                  <GraduationCap className="w-5 h-5" />
                </div>
                <span className="font-bold text-xl tracking-tight text-gray-900">Dershane AI</span>
              </div>
              
              {/* Navigation Links */}
              <nav className="ml-8 flex space-x-8">
                <Link
                  to="/dashboard"
                  className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium transition-colors
                    ${isActive('/dashboard') || location.pathname === '/' 
                      ? 'border-blue-500 text-gray-900' 
                      : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                    }`}
                >
                  <LayoutDashboard className="w-4 h-4 mr-2" />
                  Kurum Paneli
                </Link>
                <Link
                  to="/upload"
                  className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium transition-colors
                    ${isActive('/upload')
                      ? 'border-blue-500 text-gray-900' 
                      : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                    }`}
                >
                  <Upload className="w-4 h-4 mr-2" />
                  PDF Yükle
                </Link>
                <Link
                  to="/students"
                  className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium transition-colors
                    ${isActive('/students') 
                      ? 'border-blue-500 text-gray-900' 
                      : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                    }`}
                >
                  <Users className="w-4 h-4 mr-2" />
                  Öğrenciler
                </Link>
                <Link
                  to="/exams"
                  className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium transition-colors
                    ${isActive('/exams')
                      ? 'border-red-500 text-gray-900' 
                      : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                    }`}
                >
                  <span className="w-4 h-4 mr-2">⚙️</span>
                  Sınav Yönetimi
                </Link>
              </nav>
            </div>
            
            {/* User Profile Placeholder */}
            <div className="flex items-center">
              <div className="flex items-center gap-2 cursor-pointer p-2 rounded-lg hover:bg-gray-50 transition-colors">
                <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 font-bold text-sm">
                  AD
                </div>
                <span className="text-sm font-medium text-gray-700 hidden sm:block">Admin</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 w-full bg-gray-50">
        <div className="mx-auto w-full">
          {children}
        </div>
      </main>
      
      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-auto">
        <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
          <p className="text-center text-sm text-gray-500">
            &copy; {new Date().getFullYear()} Dershane Projesi. MVP Faz 6.
          </p>
        </div>
      </footer>
    </div>
  );
}
