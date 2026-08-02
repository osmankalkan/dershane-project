import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

export default function PerformanceLineChart({ chartData, subjects }) {
  const colors = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#14b8a6"];

  if (!chartData || chartData.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-gray-400">
        Grafik için yeterli sınav verisi bulunmuyor.
      </div>
    );
  }

  return (
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
  );
}
