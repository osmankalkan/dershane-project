import React from 'react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip } from 'recharts';

export default function SubjectRadarChart({ radarData }) {
  if (!radarData || radarData.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-gray-400">
        Radar grafiği için veri bulunmuyor.
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height="100%">
      <RadarChart cx="50%" cy="50%" outerRadius="70%" data={radarData}>
        <PolarGrid stroke="#e5e7eb" />
        <PolarAngleAxis dataKey="subject" tick={{ fill: '#4b5563', fontSize: 12, fontWeight: 500 }} />
        <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
        <Tooltip 
          contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }}
          formatter={(value) => [`%${value.toFixed(1)}`, 'Başarı Yüzdesi']}
        />
        <Radar
          name="Başarı"
          dataKey="success_rate"
          stroke="#6366f1"
          strokeWidth={2}
          fill="#818cf8"
          fillOpacity={0.5}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
}
