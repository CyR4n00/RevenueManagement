import React, { useState, useEffect } from 'react';

interface CalendarModalProps {
  onClose: () => void;
  basePrice: number;
}

export function CalendarModal({ onClose, basePrice }: CalendarModalProps) {
  const [days, setDays] = useState<{date: number, price: number, isHigh: boolean}[]>([]);
  const month = "2026年 5月";

  useEffect(() => {
    // Generate dummy calendar data with past costs
    const dummyDays = [];
    for (let i = 1; i <= 31; i++) {
      const isWeekend = (i % 7 === 2) || (i % 7 === 3); // roughly Friday/Saturday
      const multiplier = isWeekend ? 1.3 : (Math.random() * 0.2 + 0.9); // 0.9 ~ 1.1
      const price = Math.round((basePrice * multiplier) / 100) * 100;
      dummyDays.push({
        date: i,
        price: price,
        isHigh: price > basePrice * 1.1
      });
    }
    setDays(dummyDays);
  }, [basePrice]);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden">

        <div className="flex justify-between items-center p-4 border-b bg-gray-50">
          <h2 className="text-lg font-bold text-gray-800">過去の費用（販売価格）カレンダー表示</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-800 font-bold text-xl">&times;</button>
        </div>

        <div className="p-6 overflow-y-auto">
          <div className="flex justify-between items-center mb-4">
             <h3 className="text-xl font-bold">{month} の実績</h3>
             <div className="flex space-x-4 text-xs font-bold">
               <span className="flex items-center"><div className="w-3 h-3 bg-red-100 border border-red-300 mr-1"></div>高需要 (高単価)</span>
               <span className="flex items-center"><div className="w-3 h-3 bg-white border border-gray-300 mr-1"></div>通常</span>
             </div>
          </div>

          <div className="grid grid-cols-7 gap-2 mb-2 text-center text-sm font-bold text-gray-500">
             <div>日</div><div>月</div><div>火</div><div>水</div><div>木</div><div>金</div><div>土</div>
          </div>

          <div className="grid grid-cols-7 gap-2">
            {/* Empty slots for May 2026 (Starts on Friday) */}
            <div className="p-2 border rounded border-transparent"></div>
            <div className="p-2 border rounded border-transparent"></div>
            <div className="p-2 border rounded border-transparent"></div>
            <div className="p-2 border rounded border-transparent"></div>
            <div className="p-2 border rounded border-transparent"></div>

            {days.map((day, i) => (
              <div key={i} className={`p-2 border rounded h-20 flex flex-col justify-between ${day.isHigh ? 'bg-red-50 border-red-200' : 'bg-white border-gray-200'}`}>
                <span className={`text-xs font-bold ${day.isHigh ? 'text-red-700' : 'text-gray-500'}`}>{day.date}</span>
                <span className="text-center font-bold text-sm text-gray-800">¥{day.price.toLocaleString()}</span>
              </div>
            ))}
          </div>

          <div className="mt-6 bg-blue-50 p-4 rounded-lg border border-blue-100">
             <h4 className="font-bold text-blue-800 text-sm mb-2">カレンダー分析インサイト</h4>
             <p className="text-sm text-gray-700">
               週末（金・土）において、基本価格（¥{basePrice.toLocaleString()}）に対して約1.3倍の価格での販売実績が確認できます。
               しかし、中旬の平日において稼働率が低下傾向にあったため、価格が若干下落しています。
               次月は平日のベース価格設定の見直しを推奨します。
             </p>
          </div>
        </div>

      </div>
    </div>
  );
}
