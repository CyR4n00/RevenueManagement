import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';
import { SettingsPanel } from './SettingsPanel';

interface Competitor {
  id: number;
  name: string;
}

interface CompetitorPrice {
  date: string;
  competitor_id: number;
  competitor_name: string;
  price_today: number;
  price_yesterday: number;
  difference: number;
  is_fully_booked: boolean;
}

interface Alert {
  id: number;
  date: string;
  message: string;
  type: string;
}

interface Recommendation {
  date: string;
  suggested_price: number;
  suggested_rank: string;
  reasoning: string;
}

const API_BASE = 'http://localhost:8000';

function App() {
  const [showSettings, setShowSettings] = useState(false);
  const [selectedDate, setSelectedDate] = useState(() => {
    const today = new Date();
    today.setFullYear(2026, 6, 20); // Base mock date: 2026-07-20 (Summer)
    return today.toISOString().split('T')[0];
  });

  const [marketData, setMarketData] = useState<CompetitorPrice[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [recommendation, setRecommendation] = useState<Recommendation | null>(null);
  const [dates, setDates] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const handleDownloadCsv = () => {
    window.open(`${API_BASE}/export_csv?start_date=${selectedDate}&days=7`, '_blank');
  };

  const fetchData = async () => {
    try {
      setIsLoading(true);
      // Calculate next 7 days starting from selected date
      const start = new Date(selectedDate);
      const d = [];
      for (let i = 0; i < 7; i++) {
        const nextDate = new Date(start);
        nextDate.setDate(start.getDate() + i);
        d.push(nextDate.toISOString().split('T')[0]);
      }
      setDates(d);

      const [marketRes, alertsRes, recRes] = await Promise.all([
        axios.get(`${API_BASE}/market_data?start_date=${selectedDate}&days=7`),
        axios.get(`${API_BASE}/alerts?start_date=${selectedDate}&days=7`),
        axios.get(`${API_BASE}/recommendation?date=${selectedDate}`)
      ]);

      setMarketData(marketRes.data);
      setAlerts(alertsRes.data);
      setRecommendation(recRes.data);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [selectedDate, showSettings]); // Refresh when date changes or settings close

  // Group market data by competitor for the Tower view
  const comps = Array.from(new Set(marketData.map(m => m.competitor_name)));

  return (
    <div className="min-h-screen bg-gray-50 p-4 md:p-8 font-sans text-gray-800">
      <div className="max-w-6xl mx-auto space-y-6">

        {/* Header Section */}
        <header className="flex flex-col md:flex-row justify-between items-start md:items-center space-y-4 md:space-y-0 bg-white p-4 rounded-xl shadow-sm border border-gray-200">
          <div>
            <h1 className="text-2xl font-bold text-gray-800 tracking-tight">レベニューアシスタント <span className="text-sm font-normal text-gray-500 ml-2">〜競合調査・価格提案ツール〜</span></h1>
          </div>
          <div className="flex space-x-3 items-center">
             <input
              type="date"
              className="p-2 border border-gray-300 rounded shadow-sm focus:ring-2 focus:ring-blue-400 outline-none font-bold text-gray-700"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
            />
            <div className="h-6 border-l border-gray-300"></div>
            <button
               aria-label={showSettings ? "ベンチマーク設定を閉じる" : "ベンチマーク設定を開く"}
               aria-expanded={showSettings}
               onClick={() => setShowSettings(!showSettings)}
               className={`text-sm font-bold border px-3 py-2 rounded transition-colors focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-blue-500 focus-visible:outline-none ${showSettings ? 'bg-gray-800 text-white border-gray-800' : 'text-gray-600 hover:bg-gray-50'}`}
             >
               ⚙️ ベンチマーク設定
            </button>
          </div>
        </header>

        {showSettings ? (
           <SettingsPanel onClose={() => setShowSettings(false)} />
        ) : (
          <div aria-busy={isLoading} className={`space-y-6 transition-opacity duration-200 ${isLoading ? 'opacity-50 pointer-events-none' : ''}`}>

            {/* Top Row: AI Suggestion & Alerts */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

              {/* AI Assistant Panel */}
              <div className="lg:col-span-1 bg-gradient-to-br from-indigo-500 to-blue-600 rounded-xl shadow-md p-5 text-white flex flex-col justify-between">
                <div>
                   <h2 className="text-xs font-bold uppercase tracking-wider text-blue-100 flex items-center">
                     <span className="text-xl mr-2">🤖</span> AI 価格提案 ({selectedDate})
                   </h2>
                   {recommendation ? (
                     <div className="mt-4">
                       <p className="text-sm text-blue-100 mb-1">推奨価格・ランク</p>
                       <div className="flex items-baseline">
                         <p className="text-5xl font-extrabold tracking-tight">
                           ランク {recommendation.suggested_rank}
                         </p>
                         <p className="ml-3 text-lg opacity-80">
                           (¥{recommendation.suggested_price.toLocaleString()})
                         </p>
                       </div>
                       <div className="mt-4 bg-white bg-opacity-20 rounded p-3 text-sm leading-relaxed">
                         {recommendation.reasoning}
                       </div>
                     </div>
                   ) : (
                     <p className="mt-4 text-blue-200">データ分析中...</p>
                   )}
                </div>
                <button
                  aria-label="サイトコントローラー用CSVをダウンロード"
                  onClick={handleDownloadCsv}
                  className="mt-6 w-full bg-white text-blue-700 font-bold py-2 rounded shadow hover:bg-blue-50 transition-colors text-sm focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-blue-300 focus-visible:outline-none"
                >
                  📥 サイトコントローラー用CSVをダウンロード
                </button>
              </div>

              {/* Alerts Panel */}
              <div className="lg:col-span-2 bg-white rounded-xl shadow-sm border border-gray-200 p-5 flex flex-col">
                 <h2 className="text-sm font-bold text-gray-800 mb-4 flex items-center">
                   <span className="mr-2">🚨</span> 競合の重要変動アラート
                 </h2>
                 <div className="flex-1 overflow-y-auto space-y-3 max-h-64 pr-2">
                   {alerts.length === 0 ? (
                     <p className="text-gray-400 text-sm mt-4 text-center">直近で大きな価格変動はありません。</p>
                   ) : (
                     alerts.map(alert => (
                       <div key={alert.id} className={`p-3 rounded-lg border-l-4 text-sm flex items-start ${
                         alert.type === 'increase' ? 'bg-red-50 border-red-500 text-red-900' :
                         alert.type === 'decrease' ? 'bg-blue-50 border-blue-500 text-blue-900' :
                         'bg-yellow-50 border-yellow-500 text-yellow-900'
                       }`}>
                         <span className="font-bold mr-2 mt-0.5">
                           {alert.type === 'increase' ? '↑ 値上げ' : alert.type === 'decrease' ? '↓ 値下げ' : '満室'}
                         </span>
                         <span className="leading-snug">{alert.message}</span>
                       </div>
                     ))
                   )}
                 </div>
              </div>
            </div>

            {/* Revenue Tower (Competitor Matrix) */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
               <div className="bg-gray-800 p-4 flex justify-between items-center">
                 <div>
                   <h2 className="text-lg font-bold text-white tracking-wider">レベニューカレンダー</h2>
                   <p className="text-xs text-gray-300 mt-1">ベンチマーク施設の価格変動（前日比）一覧</p>
                 </div>
                 <div className="flex space-x-3 text-xs">
                   <span className="flex items-center text-white"><div className="w-3 h-3 bg-red-100 border border-red-300 mr-1 rounded-sm"></div>値上げ</span>
                   <span className="flex items-center text-white"><div className="w-3 h-3 bg-blue-100 border border-blue-300 mr-1 rounded-sm"></div>値下げ</span>
                   <span className="flex items-center text-white"><div className="w-3 h-3 bg-gray-600 border border-gray-500 mr-1 rounded-sm"></div>満室</span>
                 </div>
               </div>

               <div className="overflow-x-auto">
                 <table className="w-full text-left border-collapse">
                   <thead>
                     <tr>
                       <th className="p-3 border-b border-r bg-gray-50 font-bold text-gray-600 text-sm min-w-[150px]">ベンチマーク施設</th>
                       {dates.map(dateStr => {
                          const d = new Date(dateStr);
                          const isWeekend = d.getDay() === 0 || d.getDay() === 6;
                          return (
                           <th key={dateStr} className={`p-3 border-b text-center text-sm font-bold min-w-[120px] ${isWeekend ? 'text-red-600 bg-red-50' : 'text-gray-700 bg-gray-50'}`}>
                             {d.getMonth()+1}/{d.getDate()} ({['日','月','火','水','木','金','土'][d.getDay()]})
                           </th>
                         )
                       })}
                     </tr>
                   </thead>
                   <tbody>
                     {comps.map(compName => (
                       <tr key={compName} className="border-b hover:bg-gray-50">
                         <td className="p-3 border-r font-bold text-sm text-gray-800">{compName}</td>
                         {dates.map(dateStr => {
                           const data = marketData.find(m => m.competitor_name === compName && m.date === dateStr);
                           if (!data) return <td key={dateStr} className="p-3 text-center text-gray-300">-</td>;

                           if (data.is_fully_booked) {
                             return (
                               <td key={dateStr} className="p-3 text-center bg-gray-100 border-x border-gray-50">
                                 <span className="text-xs font-bold text-gray-500 bg-gray-200 px-2 py-1 rounded">満室 (×)</span>
                               </td>
                             );
                           }

                           const isUp = data.difference > 0;
                           const isDown = data.difference < 0;
                           const bgClass = isUp ? 'bg-red-50' : isDown ? 'bg-blue-50' : 'bg-white';
                           const diffColor = isUp ? 'text-red-600' : isDown ? 'text-blue-600' : 'text-gray-400';

                           return (
                             <td key={dateStr} className={`p-3 text-center border-x border-gray-50 ${bgClass}`}>
                               <div className="font-bold text-gray-800 tracking-tight">¥{data.price_today.toLocaleString()}</div>
                               <div className={`text-[10px] font-bold mt-1 ${diffColor}`}>
                                 {isUp ? '▲ +' : isDown ? '▼ ' : '▶ '}{Math.abs(data.difference).toLocaleString()}
                               </div>
                             </td>
                           );
                         })}
                       </tr>
                     ))}
                   </tbody>
                 </table>
               </div>
            </div>

          </div>
        )}
      </div>
    </div>
  );
}

export default App;
