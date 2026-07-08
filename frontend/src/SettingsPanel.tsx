import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE = 'http://localhost:8000';

export function SettingsPanel({ onClose }: { onClose: () => void }) {
  const [apifyKey, setApifyKey] = useState('');
  const [competitors, setCompetitors] = useState([
    { id: 101, name: 'ホテルA (近隣リゾート)', url: 'https://travel.rakuten.co.jp/HOTEL/12345/' },
    { id: 102, name: 'ゲストハウスB (駅前)', url: 'https://www.booking.com/hotel/jp/sample.html' },
    { id: 103, name: 'Cヴィラ (一棟貸し)', url: 'https://www.airbnb.jp/rooms/98765' }
  ]);

  useEffect(() => {
    // Fetch current API key on load
    axios.get(`${API_BASE}/config/apify-key`)
      .then(res => {
        if (res.data && res.data.value) {
          setApifyKey(res.data.value);
        }
      })
      .catch(err => console.error("Failed to fetch API key:", err));
  }, []);

  const handleSave = async () => {
    try {
      await axios.post(`${API_BASE}/config/apify-key`, {
        key: 'APIFY_API_TOKEN',
        value: apifyKey
      });
      onClose();
    } catch (err) {
      console.error("Failed to save API key:", err);
      alert("設定の保存に失敗しました。");
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden mt-6 mb-8">
      <div className="bg-gray-50 border-b p-4 flex justify-between items-center">
        <div>
          <h2 className="font-bold text-lg text-gray-800">⚙️ 管理者専用セットアップ</h2>
          <p className="text-xs text-gray-500 mt-1">この画面は導入時のセットアップ用です。運用時にクライアントが触る必要はありません。</p>
        </div>
        <button onClick={onClose} className="text-gray-500 hover:text-gray-800 font-bold text-xl">&times;</button>
      </div>

      <div className="p-6 space-y-8">
        {/* Competitor Settings */}
        <div>
          <h3 className="font-bold text-gray-700 mb-4 border-b pb-2">1. ベンチマーク（競合）登録</h3>
          <div className="space-y-4">
            {competitors.map((comp, index) => (
              <div key={comp.id} className="border rounded-lg p-4 bg-gray-50 flex flex-col md:flex-row items-start md:items-center space-y-3 md:space-y-0 md:space-x-4">
                 <div className="bg-blue-100 text-blue-800 font-bold w-8 h-8 rounded-full flex items-center justify-center shrink-0">
                   {index + 1}
                 </div>
                 <div className="flex-1 w-full">
                   <label className="block text-xs font-bold text-gray-500 mb-1">施設名 (表示用)</label>
                   <input type="text" className="w-full p-2 border rounded text-sm focus:ring-2 focus:ring-blue-400 outline-none" defaultValue={comp.name} />
                 </div>
                 <div className="flex-2 w-full md:w-1/2">
                   <label className="block text-xs font-bold text-gray-500 mb-1">OTAのURL (楽天トラベル, Booking.com等)</label>
                   <input type="text" className="w-full p-2 border rounded text-sm focus:ring-2 focus:ring-blue-400 outline-none" defaultValue={comp.url} />
                 </div>
              </div>
            ))}
          </div>
          <div className="mt-4 text-xs text-gray-500 flex items-start bg-gray-50 p-3 rounded border">
            <span className="mr-2">ℹ️</span>
            <p>※現在は直感的な把握を優先し「対象施設のその日の最安値（Best Available Rate）」を基準に比較します。将来のアップデートにて「部屋タイプ」や「食事有無」を指定した厳密なプラン比較が可能になる予定です。</p>
          </div>
        </div>

        {/* Guardrails (Min/Max Price) Settings */}
        <div>
          <div className="flex items-center justify-between border-b pb-2 mb-4">
            <h3 className="font-bold text-gray-700">2. 価格変動リミッター（ガードレール）</h3>
            <span className="bg-red-100 text-red-800 text-[10px] px-2 py-1 rounded font-bold">必須設定</span>
          </div>
          <p className="text-sm text-gray-600 mb-4">
            AIが極端な値下げや非現実的な値上げを提案しないよう、自社ホテルの価格の「下限」と「上限」を設定します。AIの提案は必ずこの範囲内に収まります。
          </p>
          <div className="flex space-x-4">
            <div className="flex-1">
              <label htmlFor="min_price" className="block text-xs font-bold text-gray-500 mb-1">最低販売価格（これ以上は下げない）</label>
              <div className="relative">
                <span className="absolute left-3 top-2 text-gray-500">¥</span>
                <input id="min_price" type="number" defaultValue="5000" className="w-full pl-8 p-2 border rounded text-sm focus:ring-2 focus:ring-blue-400 outline-none" />
              </div>
            </div>
            <div className="flex-1">
              <label htmlFor="max_price" className="block text-xs font-bold text-gray-500 mb-1">最高販売価格（これ以上は上げない）</label>
              <div className="relative">
                <span className="absolute left-3 top-2 text-gray-500">¥</span>
                <input id="max_price" type="number" defaultValue="30000" className="w-full pl-8 p-2 border rounded text-sm focus:ring-2 focus:ring-blue-400 outline-none" />
              </div>
            </div>
          </div>
        </div>

        {/* Notifications Settings */}
        <div>
          <div className="flex items-center justify-between border-b pb-2 mb-4">
            <h3 className="font-bold text-gray-700">3. 変動アラートの外部通知設定</h3>
            <span className="bg-blue-100 text-blue-800 text-[10px] px-2 py-1 rounded font-bold">推奨機能</span>
          </div>
          <p className="text-sm text-gray-600 mb-4">
            競合施設が大きな値上げ・値下げを行った際や満室になった際に、即座に通知を受け取ることができます。<br/>
            <span className="text-red-500 font-semibold text-xs">※毎日のPC確認が不要になるため、LINE連携を強く推奨します。</span>
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-4">
            <div className="border p-4 rounded-lg bg-green-50 border-green-200">
               <h4 className="font-bold text-green-700 flex items-center mb-3">
                 <span className="mr-2">💬</span> LINE通知連携
               </h4>
               <label className="flex items-center space-x-2 text-sm text-gray-700 mb-2">
                 <input type="checkbox" defaultChecked={true} className="rounded text-green-600 focus:ring-green-500" />
                 <span>LINEで通知を受け取る</span>
               </label>
               <button className="w-full bg-[#06C755] text-white font-bold py-2 rounded shadow hover:bg-green-600 transition-colors text-sm mt-2">
                 LINEアカウントと連携する
               </button>
            </div>

            <div className="border p-4 rounded-lg bg-gray-50">
               <h4 className="font-bold text-gray-700 flex items-center mb-3">
                 <span className="mr-2">📧</span> メール通知
               </h4>
               <label className="flex items-center space-x-2 text-sm text-gray-700 mb-2">
                 <input type="checkbox" defaultChecked={false} className="rounded text-blue-600 focus:ring-blue-500" />
                 <span>メールで通知を受け取る</span>
               </label>
               <input type="email" placeholder="example@hotel.com" className="w-full p-2 border rounded text-sm focus:ring-2 focus:ring-blue-400 outline-none mt-1" />
            </div>
          </div>

          {/* Advanced Notification Filters */}
          <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
             <h4 className="text-sm font-bold text-gray-700 mb-3">通知の頻度と条件（スパム防止）</h4>
             <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
               <div>
                 <label className="block text-xs font-bold text-gray-500 mb-1">通知を送る「価格変動」のしきい値</label>
                 <select className="w-full p-2 border rounded text-sm focus:ring-2 focus:ring-blue-400 outline-none bg-white" defaultValue="3000">
                   <option value="1000">1,000円以上の変動で通知</option>
                   <option value="3000">3,000円以上の変動で通知 (推奨)</option>
                   <option value="5000">5,000円以上の変動で通知</option>
                 </select>
               </div>
               <div>
                 <label className="block text-xs font-bold text-gray-500 mb-1">通知のタイミング</label>
                 <select className="w-full p-2 border rounded text-sm focus:ring-2 focus:ring-blue-400 outline-none bg-white" defaultValue="morning">
                   <option value="immediate">変動を検知したら即時</option>
                   <option value="morning">1日1回 朝10時にまとめて通知 (推奨)</option>
                   <option value="evening">1日1回 夕方17時にまとめて通知</option>
                 </select>
               </div>
             </div>
          </div>
        </div>

        {/* API Key Settings */}
        <div>
          <div className="flex items-center justify-between border-b pb-2 mb-4">
            <h3 className="font-bold text-gray-700">4. データ連携設定 (APIキー)</h3>
            <span className="bg-red-100 text-red-800 text-[10px] px-2 py-1 rounded font-bold">必須設定</span>
          </div>
          <p className="text-sm text-gray-600 mb-4">
            実際の競合価格データを取得するためには、ApifyのAPIキーが必要です。
          </p>
          <div className="w-full">
            <label htmlFor="apify_key" className="block text-xs font-bold text-gray-500 mb-1">Apify API Token</label>
            <input
              id="apify_key"
              type="password"
              placeholder="apify_api_..."
              value={apifyKey}
              onChange={(e) => setApifyKey(e.target.value)}
              className="w-full p-2 border rounded text-sm focus:ring-2 focus:ring-blue-400 outline-none"
            />
          </div>
        </div>

        <div className="flex justify-end pt-4 border-t">
          <button onClick={handleSave} className="bg-blue-600 text-white px-6 py-2 rounded-lg font-bold shadow hover:bg-blue-700 transition-colors">
            設定を保存して戻る
          </button>
        </div>
      </div>
    </div>
  );
}
