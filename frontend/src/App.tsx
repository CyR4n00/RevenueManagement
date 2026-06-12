import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { SettingsPanel } from './SettingsPanel';
import { CalendarModal } from './CalendarModal';
import { RulesConfig } from './RulesConfig';

interface Facility {
  id: number;
  name: string;
  base_price: number;
  min_price: number;
  max_price: number;
  total_rooms: number;
  max_sell_rooms: number;
  plan: string;
  custom_event_multiplier: number;
}

interface PriceRecommendation {
  facility_id: number;
  date: string;
  recommended_price_rule_based: number;
  rule_applied: string | null;
  recommended_price_ml_based: number | null;
  event_multiplier: number;
  final_price: number;
}

interface OccupancyData {
  facility_id: number;
  date: string;
  booked_rooms: number;
}

interface Rule {
  id: number;
  facility_id: number;
  occupancy_threshold_percent: number;
  price_multiplier: number;
  active: boolean;
}

interface PerformanceData {
  facility_id: number;
  month: string;
  target_revenue: number;
  actual_revenue: number;
}

interface SuggestionData {
  facility_id: number;
  date_generated: string;
  suggestion_text: string;
}

function App() {
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [selectedFacility, setSelectedFacility] = useState<number | null>(null);
  const [selectedDate, setSelectedDate] = useState<string>(new Date().toISOString().split('T')[0]);
  const [recommendation, setRecommendation] = useState<PriceRecommendation | null>(null);
  const [occupancy, setOccupancy] = useState<OccupancyData | null>(null);
  const [rules, setRules] = useState<Rule[]>([]);
  const [performance, setPerformance] = useState<PerformanceData[]>([]);
  const [suggestion, setSuggestion] = useState<SuggestionData | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [showCalendar, setShowCalendar] = useState(false);

  const refreshAll = () => {
    fetchFacilities();
    if (selectedFacility && selectedDate) {
      fetchDashboardData(selectedFacility, selectedDate);
      fetchRules(selectedFacility);
    }
  }

  useEffect(() => {
    fetchFacilities();
  }, []);

  useEffect(() => {
    if (selectedFacility && selectedDate) {
      fetchDashboardData(selectedFacility, selectedDate);
      fetchRules(selectedFacility);
      fetchPerformance(selectedFacility);
      fetchSuggestion(selectedFacility);
    }
  }, [selectedFacility, selectedDate]);

  const fetchFacilities = async () => {
    try {
      const response = await axios.get('http://localhost:8000/facilities');
      setFacilities(response.data);
      if (response.data.length > 0 && selectedFacility === null) {
        setSelectedFacility(response.data[0].id);
      }
    } catch (error) {
      console.error("施設の取得に失敗しました:", error);
    }
  };

  const fetchRules = async (facilityId: number) => {
    try {
      const response = await axios.get(`http://localhost:8000/rules?facility_id=${facilityId}`);
      setRules(response.data);
    } catch (error) {
      console.error("ルールの取得に失敗しました:", error);
    }
  };

  const fetchPerformance = async (facilityId: number) => {
    try {
      const response = await axios.get(`http://localhost:8000/performance/${facilityId}`);
      setPerformance(response.data);
    } catch (error) {
      console.error("パフォーマンスデータの取得に失敗しました:", error);
    }
  }

  const fetchSuggestion = async (facilityId: number) => {
    try {
      const response = await axios.get(`http://localhost:8000/suggestions/${facilityId}`);
      setSuggestion(response.data);
    } catch (error) {
      console.error("サジェストデータの取得に失敗しました:", error);
    }
  }

  const fetchDashboardData = async (facilityId: number, date: string) => {
    try {
      setRecommendation(null);
      const occResponse = await axios.get(`http://localhost:8000/occupancy?facility_id=${facilityId}&date=${date}`);
      const dayOcc = occResponse.data.find((o: any) => o.date === date);
      setOccupancy(dayOcc || null);

      const recResponse = await axios.get(`http://localhost:8000/recommendations/${facilityId}/${date}`);
      setRecommendation(recResponse.data);
    } catch (error) {
      console.error("ダッシュボードデータの取得に失敗しました:", error);
      setRecommendation(null);
      setOccupancy(null);
    }
  };

  const selectedFacilityData = facilities.find(f => f.id === selectedFacility);

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header Section */}
        <header className="flex flex-col md:flex-row justify-between items-start md:items-center space-y-4 md:space-y-0 bg-white p-4 rounded-xl shadow-sm border border-gray-200">
          <div>
            <h1 className="text-2xl font-bold text-gray-800 tracking-tight">レベニューコントロール</h1>
            {selectedFacilityData && (
              <p className="text-sm text-gray-500 mt-1">
                契約プラン: <span className="font-semibold text-blue-600 bg-blue-50 px-2 py-0.5 rounded">{selectedFacilityData.plan}</span>
              </p>
            )}
          </div>
          <div className="flex space-x-3 items-center">
             <button
               onClick={() => setShowSettings(!showSettings)}
               className={`text-sm font-bold border px-3 py-2 rounded transition-colors ${showSettings ? 'bg-blue-600 text-white border-blue-600' : 'text-gray-600 hover:bg-gray-50'}`}
             >
               ⚙️ 施設・連携設定
             </button>
             <div className="h-6 border-l border-gray-300"></div>
             <input
              type="date"
              className="p-2 border border-gray-300 rounded shadow-sm focus:ring-2 focus:ring-blue-400 outline-none"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
            />
            <select
              className="p-2 border border-gray-300 rounded shadow-sm focus:ring-2 focus:ring-blue-400 outline-none bg-white font-bold"
              value={selectedFacility || ''}
              onChange={(e) => {
                setSelectedFacility(Number(e.target.value));
                setShowSettings(false);
              }}
            >
              {facilities.map(f => (
                <option key={f.id} value={f.id}>{f.name}</option>
              ))}
            </select>
          </div>
        </header>

        {showSettings && selectedFacilityData && (
           <SettingsPanel facilityId={selectedFacility!} facilityData={selectedFacilityData} onUpdate={refreshAll} />
        )}

        {/* Top KPIs */}
        {!showSettings && selectedFacilityData && (
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <div className="bg-white rounded-xl shadow-sm p-5 border border-gray-100 flex flex-col justify-between">
              <h2 className="text-xs font-bold text-gray-400 uppercase tracking-wider">稼働率予測 ({selectedDate})</h2>
              {occupancy ? (
                <div>
                  <p className="text-4xl font-extrabold text-gray-800 mt-2">
                    {Math.round((occupancy.booked_rooms / selectedFacilityData.max_sell_rooms) * 100)}<span className="text-xl font-normal text-gray-500">%</span>
                  </p>
                  <p className="text-xs text-gray-400 mt-1">{occupancy.booked_rooms} / {selectedFacilityData.max_sell_rooms} 室 (販売上限ブロック)</p>
                </div>
              ) : (
                <p className="text-lg text-gray-400 mt-2">データなし</p>
              )}
            </div>

            <div className="col-span-1 md:col-span-2 bg-gradient-to-r from-blue-500 to-indigo-600 rounded-xl shadow-md p-5 text-white flex flex-col justify-between">
              <div className="flex justify-between items-start">
                 <h2 className="text-xs font-bold uppercase tracking-wider text-blue-100">最終算出価格 (OTA同期予定)</h2>
                 <span className="bg-white text-indigo-600 text-[10px] font-bold px-2 py-1 rounded-full">Best Available Rate</span>
              </div>
              {recommendation ? (
                <div>
                  <p className="text-4xl font-extrabold mt-2">
                    <span className="text-2xl mr-1">¥</span>{recommendation.final_price.toLocaleString()}
                  </p>
                  <div className="text-xs text-blue-100 mt-2 flex items-center space-x-2 bg-black bg-opacity-20 inline-block px-2 py-1 rounded">
                    <span>上限: ¥{selectedFacilityData.max_price.toLocaleString()}</span>
                    <span>|</span>
                    <span>下限: ¥{selectedFacilityData.min_price.toLocaleString()}</span>
                  </div>
                </div>
              ) : (
                <p className="text-lg mt-2">計算中...</p>
              )}
            </div>

            <div className="col-span-1 md:col-span-2 bg-white rounded-xl shadow-sm p-5 border border-gray-100">
               <h2 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">算出内訳</h2>
               {recommendation ? (
                 <div className="space-y-3">
                    <div className="flex justify-between items-center text-sm border-b pb-1">
                      <span className="text-gray-500">基本価格</span>
                      <span className="font-semibold text-gray-800">¥{selectedFacilityData.base_price.toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between items-center text-sm border-b pb-1">
                      <span className="text-gray-500">週末・イベント手動加算 (Pro機能)</span>
                      <span className="font-semibold text-green-600">{recommendation.event_multiplier > 1.0 ? `x${recommendation.event_multiplier}` : '-'}</span>
                    </div>
                    {selectedFacilityData.plan === "Enterprise" ? (
                      <div className="flex justify-between items-center text-sm border-b pb-1">
                        <span className="text-purple-600 font-semibold flex items-center">
                          <span className="mr-1">🤖</span> AI需要予測 (Enterprise機能)
                        </span>
                        <span className="font-bold text-purple-700">¥{recommendation.recommended_price_ml_based?.toLocaleString()}</span>
                      </div>
                    ) : (
                      <div className="flex justify-between items-center text-sm border-b pb-1">
                        <span className="text-blue-600 flex items-center">
                          <span className="mr-1">⚙️</span> ルールベース適用
                        </span>
                        <span className="font-semibold text-gray-800">¥{recommendation.recommended_price_rule_based.toLocaleString()}</span>
                      </div>
                    )}
                 </div>
               ) : (
                 <p className="text-sm text-gray-400">ロード中...</p>
               )}
            </div>
          </div>
        )}

        {!showSettings && selectedFacilityData && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

            {/* Custom Rules Section */}
            <RulesConfig
              rules={rules}
              facilityId={selectedFacilityData.id}
              onRuleChanged={() => {
                fetchRules(selectedFacilityData.id);
                fetchDashboardData(selectedFacilityData.id, selectedDate);
              }}
            />

            {/* Performance & PDCA Section */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden flex flex-col">
              <div className="bg-gray-50 p-4 border-b">
                <h2 className="text-lg font-bold text-gray-800">効果検証ダッシュボード (PDCA)</h2>
                <p className="text-xs text-gray-500 mt-1">需要予測 ▷ 販売 ▷ 検証 のサイクル可視化</p>
              </div>

              {suggestion && (
                <div className="bg-yellow-50 p-3 border-b border-yellow-100 flex items-start">
                  <span className="text-xl mr-2">💡</span>
                  <p className="text-xs text-yellow-800 font-bold leading-tight">{suggestion.suggestion_text}</p>
                </div>
              )}

              <div className="p-4 space-y-4">
                <h3 className="text-sm font-bold text-gray-600 border-b pb-1">直近の収益比較</h3>
                 {performance.map((p, index) => {
                   const diff = p.actual_revenue - p.target_revenue;
                   const isPositive = diff >= 0;
                   return (
                   <div key={index} className="border rounded-lg p-3">
                     <div className="flex justify-between items-center mb-2">
                       <span className="font-bold text-gray-700">{p.month}</span>
                       <span className={`text-xs font-bold px-2 py-1 rounded ${isPositive ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                         {isPositive ? '+' : ''}{Math.round((diff / p.target_revenue)*100)}%
                       </span>
                     </div>
                     <div className="w-full bg-gray-200 rounded-full h-2.5 mb-1 dark:bg-gray-700 relative">
                        <div className="bg-blue-200 h-2.5 rounded-full absolute top-0 left-0" style={{ width: '100%' }}></div>
                        <div className="bg-blue-600 h-2.5 rounded-full absolute top-0 left-0" style={{ width: `${Math.min(100, (p.actual_revenue/p.target_revenue)*100)}%` }}></div>
                     </div>
                     <div className="flex justify-between text-[10px] text-gray-500">
                       <span>目標: ¥{(p.target_revenue/10000).toLocaleString()}万</span>
                       <span>実績: ¥{(p.actual_revenue/10000).toLocaleString()}万</span>
                     </div>
                   </div>
                 )})}
                 <button
                   onClick={() => setShowCalendar(true)}
                   className="w-full mt-2 text-xs font-bold text-blue-600 border border-blue-200 bg-blue-50 py-2 rounded hover:bg-blue-100 transition-colors"
                 >
                   📅 カレンダーで過去の費用詳細を確認する
                 </button>
              </div>
            </div>
          </div>
        )}

        {/* Guest UI Mock */}
        {!showSettings && (
          <div className="mt-8 border-t pt-8">
             <h2 className="text-sm font-bold text-gray-500 mb-4 uppercase tracking-wider">ゲスト向けUIウィジェット（デモ）</h2>
             <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200 max-w-sm">
                <p className="text-xs text-gray-600 mb-3 text-center font-bold">当施設の料金は空室状況により3段階で変動します</p>
                <div className="flex justify-between text-center text-xs font-medium">
                  <div className="flex-1 flex flex-col items-center">
                    <div className="w-4 h-4 rounded-full bg-green-400 mb-1"></div>
                    <span className="text-green-700">おトク</span>
                  </div>
                  <div className="flex-1 flex flex-col items-center">
                    <div className="w-4 h-4 rounded-full bg-yellow-400 mb-1"></div>
                    <span className="text-yellow-700">通常</span>
                  </div>
                  <div className="flex-1 flex flex-col items-center">
                    <div className="w-4 h-4 rounded-full bg-red-400 mb-1"></div>
                    <span className="text-red-700">混雑</span>
                  </div>
                </div>
             </div>
          </div>
        )}

      </div>

      {showCalendar && selectedFacilityData && (
        <CalendarModal
          onClose={() => setShowCalendar(false)}
          basePrice={selectedFacilityData.base_price}
        />
      )}
    </div>
  );
}

export default App;
