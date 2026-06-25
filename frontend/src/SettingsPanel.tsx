import React, { useState } from 'react';

export function SettingsPanel({ onClose }: { onClose: () => void }) {
  const [competitors, setCompetitors] = useState([
    { id: 101, name: 'ホテルA (近隣リゾート)', url: 'https://travel.rakuten.co.jp/HOTEL/12345/' },
    { id: 102, name: 'ゲストハウスB (駅前)', url: 'https://www.booking.com/hotel/jp/sample.html' },
    { id: 103, name: 'Cヴィラ (一棟貸し)', url: 'https://www.airbnb.jp/rooms/98765' }
  ]);

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden mt-6 mb-8">
      <div className="bg-gray-50 border-b p-4 flex justify-between items-center">
        <div>
          <h2 className="font-bold text-lg text-gray-800">⚙️ アシスタント設定 (ベンチマーク・通知)</h2>
          <p className="text-xs text-gray-500 mt-1">AIが毎日監視する競合施設と、アラートの通知先を設定します。</p>
        </div>
        <button onClick={onClose} aria-label="閉じる" className="text-gray-500 hover:text-gray-800 font-bold text-xl focus-visible:ring-2 focus-visible:outline-none rounded">&times;</button>
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
                   <label htmlFor={`comp-name-${comp.id}`} className="block text-xs font-bold text-gray-500 mb-1">施設名 (表示用)</label>
                   <input id={`comp-name-${comp.id}`} type="text" className="w-full p-2 border rounded text-sm focus:ring-2 focus:ring-blue-400 outline-none" defaultValue={comp.name} />
                 </div>
                 <div className="flex-2 w-full md:w-1/2">
                   <label htmlFor={`comp-url-${comp.id}`} className="block text-xs font-bold text-gray-500 mb-1">OTAのURL (楽天トラベル, Booking.com等)</label>
                   <input id={`comp-url-${comp.id}`} type="text" className="w-full p-2 border rounded text-sm focus:ring-2 focus:ring-blue-400 outline-none" defaultValue={comp.url} />
                 </div>
              </div>
            ))}
          </div>
          <div className="mt-4 text-xs text-gray-500 flex items-start bg-gray-50 p-3 rounded border">
            <span className="mr-2">ℹ️</span>
            <p>※現在は直感的な把握を優先し「対象施設のその日の最安値（Best Available Rate）」を基準に比較します。将来のアップデートにて「部屋タイプ」や「食事有無」を指定した厳密なプラン比較が可能になる予定です。</p>
          </div>
        </div>

        {/* Notifications Settings */}
        <div>
          <div className="flex items-center justify-between border-b pb-2 mb-4">
            <h3 className="font-bold text-gray-700">2. 変動アラートの外部通知設定</h3>
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
               <label htmlFor="line-notify" className="flex items-center space-x-2 text-sm text-gray-700 mb-2 cursor-pointer">
                 <input id="line-notify" type="checkbox" defaultChecked={true} className="rounded text-green-600 focus:ring-green-500" />
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
               <label htmlFor="email-notify" className="flex items-center space-x-2 text-sm text-gray-700 mb-2 cursor-pointer">
                 <input id="email-notify" type="checkbox" defaultChecked={false} className="rounded text-blue-600 focus:ring-blue-500" />
                 <span>メールで通知を受け取る</span>
               </label>
               <input type="email" aria-label="メールアドレス" placeholder="example@hotel.com" className="w-full p-2 border rounded text-sm focus:ring-2 focus:ring-blue-400 outline-none mt-1" />
            </div>
          </div>

          {/* Advanced Notification Filters */}
          <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
             <h4 className="text-sm font-bold text-gray-700 mb-3">通知の頻度と条件（スパム防止）</h4>
             <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
               <div>
                 <label htmlFor="notify-threshold" className="block text-xs font-bold text-gray-500 mb-1">通知を送る「価格変動」のしきい値</label>
                 <select id="notify-threshold" defaultValue="3000" className="w-full p-2 border rounded text-sm focus:ring-2 focus:ring-blue-400 outline-none bg-white">
                   <option value="1000">1,000円以上の変動で通知</option>
                   <option value="3000">3,000円以上の変動で通知 (推奨)</option>
                   <option value="5000">5,000円以上の変動で通知</option>
                 </select>
               </div>
               <div>
                 <label htmlFor="notify-timing" className="block text-xs font-bold text-gray-500 mb-1">通知のタイミング</label>
                 <select id="notify-timing" defaultValue="morning" className="w-full p-2 border rounded text-sm focus:ring-2 focus:ring-blue-400 outline-none bg-white">
                   <option value="immediate">変動を検知したら即時</option>
                   <option value="morning">1日1回 朝10時にまとめて通知 (推奨)</option>
                   <option value="evening">1日1回 夕方17時にまとめて通知</option>
                 </select>
               </div>
             </div>
          </div>
        </div>

        <div className="flex justify-end pt-4 border-t">
          <button onClick={onClose} className="bg-blue-600 text-white px-6 py-2 rounded-lg font-bold shadow hover:bg-blue-700 transition-colors">
            設定を保存して戻る
          </button>
        </div>
      </div>
    </div>
  );
}
