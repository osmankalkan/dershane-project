import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';

export default function TopicBreakdownBar({ topicData }) {
  if (!topicData || topicData.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-gray-400">
        Konu kırılımı için veri bulunmuyor.
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart
        data={topicData}
        layout="vertical"
        margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
      >
        <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} stroke="#f3f4f6" />
        <XAxis type="number" domain={[0, 100]} hide />
        <YAxis 
          type="category" 
          dataKey="topic" 
          axisLine={false} 
          tickLine={false} 
          width={150}
          tick={{ fill: '#4b5563', fontSize: 12 }} 
          tickFormatter={(value) => value && value.length > 25 ? value.substring(0, 25) + '...' : value}
        />
        <Tooltip
          cursor={{ fill: '#f9fafb' }}
          contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }}
          formatter={(value) => [`%${value.toFixed(1)}`, 'Başarı Yüzdesi']}
        />
        <Bar dataKey="success_rate" radius={[0, 4, 4, 0]} barSize={24}>
          {topicData.map((entry, index) => (
            <Cell 
              key={`cell-${index}`} 
              fill={entry.success_rate > 75 ? '#10b981' : entry.success_rate > 40 ? '#f59e0b' : '#ef4444'} 
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
