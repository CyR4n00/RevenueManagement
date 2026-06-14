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
          <h2 className="font-bold text-lg text-gray-800">ベンチマーク（競合）設定</h2>
          <p className="text-xs text-gray-500 mt-1">AIが毎日価格をチェックする対象施設を3つまで登録できます。</p>
        </div>
        <button onClick={onClose} className="text-gray-500 hover:text-gray-800 font-bold text-xl">&times;</button>
      </div>

      <div className="p-6 space-y-6">
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

        <div className="bg-blue-50 border border-blue-100 p-4 rounded-lg flex items-start">
           <span className="text-xl mr-3">💡</span>
           <div className="text-sm text-blue-900 leading-relaxed">
             <p className="font-bold mb-1">面倒な連携は不要です。</p>
             <p>競合施設のOTA（予約サイト）のURLを貼り付けるだけで、システムが自動で毎日価格と空室状況をスクレイピング（収集）し、レベニュータワーに反映させます。</p>
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
