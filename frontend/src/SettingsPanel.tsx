import React, { useState, useEffect } from 'react';
import axios from 'axios';

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

interface IntegrationSettings {
  facility_id: number;
  site_controller_type: string | null;
  site_controller_api_key: string | null;
  rakuten_enabled: boolean;
  bookingcom_enabled: boolean;
  airbnb_enabled: boolean;
  sync_mode: string;
}

interface SyncStatus {
  facility_id: number;
  last_sync_time: string;
  status: string;
  synced_ota_list: string[];
  message: string;
}

interface SettingsPanelProps {
  facilityId: number;
  facilityData: Facility;
  onUpdate: () => void;
}

export function SettingsPanel({ facilityId, facilityData, onUpdate }: SettingsPanelProps) {
  const [integrations, setIntegrations] = useState<IntegrationSettings | null>(null);
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null);
  const [activeTab, setActiveTab] = useState('facility');
  const [formData, setFormData] = useState<Facility>(facilityData);

  useEffect(() => {
    fetchIntegrations();
    fetchSyncStatus();
    setFormData(facilityData);
  }, [facilityId, facilityData]);

  const fetchIntegrations = async () => {
    try {
      const res = await axios.get(`http://localhost:8000/integrations/${facilityId}`);
      setIntegrations(res.data);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchSyncStatus = async () => {
    try {
      const res = await axios.get(`http://localhost:8000/sync_status/${facilityId}`);
      setSyncStatus(res.data);
    } catch (e) {
      console.error(e);
    }
  };

  const handleFacilitySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await axios.put(`http://localhost:8000/facilities/${facilityId}`, formData);
      alert('施設情報を保存しました。');
      onUpdate();
    } catch (e) {
      alert('エラーが発生しました。');
    }
  };

  const renderFacilityTab = () => (
    <form onSubmit={handleFacilitySubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-bold text-gray-700 mb-1">施設名</label>
          <input type="text" className="w-full p-2 border rounded" value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} />
        </div>
        <div>
          <label className="block text-sm font-bold text-gray-700 mb-1">プラン</label>
          <select className="w-full p-2 border rounded bg-gray-100 cursor-not-allowed" value={formData.plan} disabled>
            <option value="Standard">Standard</option>
            <option value="Pro">Pro</option>
            <option value="Enterprise">Enterprise</option>
          </select>
          <p className="text-[10px] text-gray-500 mt-1">※プラン変更はサポートにお問い合わせください。</p>
        </div>
        <div>
          <label className="block text-sm font-bold text-gray-700 mb-1">総客室数 (キャパシティ)</label>
          <input type="number" className="w-full p-2 border rounded" value={formData.total_rooms} onChange={e => setFormData({...formData, total_rooms: Number(e.target.value)})} />
        </div>
        <div>
          <label className="block text-sm font-bold text-blue-600 mb-1">販売上限室数 (ブロック)</label>
          <input type="number" className="w-full p-2 border rounded border-blue-300" value={formData.max_sell_rooms} onChange={e => setFormData({...formData, max_sell_rooms: Number(e.target.value)})} />
          <p className="text-[10px] text-gray-500 mt-1">オーバーブッキングを防ぐため、ここで設定した室数に達すると売り止めします。</p>
        </div>
        <div>
          <label className="block text-sm font-bold text-gray-700 mb-1">基本価格</label>
          <input type="number" className="w-full p-2 border rounded" value={formData.base_price} onChange={e => setFormData({...formData, base_price: Number(e.target.value)})} />
        </div>
        <div>
          <label className="block text-sm font-bold text-green-600 mb-1">週末・イベント加算倍率 (Pro以上)</label>
          <div className="flex items-center space-x-2">
            <input type="number" step="0.1" className="w-full p-2 border rounded border-green-300" value={formData.custom_event_multiplier} onChange={e => setFormData({...formData, custom_event_multiplier: Number(e.target.value)})} />
            <span>倍</span>
          </div>
          <p className="text-[10px] text-gray-500 mt-1">過去の知見や周辺イベントを考慮し、週末などに自動で掛ける倍率を設定します。</p>
        </div>

        <div className="col-span-2 grid grid-cols-2 gap-4 border p-3 rounded bg-red-50 border-red-100">
           <div>
             <label className="block text-sm font-bold text-red-600 mb-1">下限価格 (Safety Limit)</label>
             <input type="number" className="w-full p-2 border rounded" value={formData.min_price} onChange={e => setFormData({...formData, min_price: Number(e.target.value)})} />
           </div>
           <div>
             <label className="block text-sm font-bold text-red-600 mb-1">上限価格 (Safety Limit)</label>
             <input type="number" className="w-full p-2 border rounded" value={formData.max_price} onChange={e => setFormData({...formData, max_price: Number(e.target.value)})} />
           </div>
           <p className="text-xs text-red-500 col-span-2 font-semibold">※AIやルールが計算した価格でも、絶対にこの金額の範囲内に収める「安全装置」です。</p>
        </div>
      </div>
      <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded font-bold hover:bg-blue-700">設定を保存</button>
    </form>
  );

  const renderIntegrationTab = () => (
    <div className="space-y-6">
      {integrations && (
        <div className="bg-white p-4 border rounded shadow-sm">
           <h3 className="font-bold text-lg mb-4">OTA・サイトコントローラー API連携設定</h3>

           <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
             <div className="border p-4 rounded bg-gray-50">
               <h4 className="font-semibold text-gray-700 mb-2">サイトコントローラー設定</h4>
               <label className="block text-sm text-gray-600 mb-1">利用プロバイダ</label>
               <select className="w-full p-2 border rounded mb-3" defaultValue={integrations.site_controller_type || ''}>
                 <option value="">(使用しない)</option>
                 <option value="neppan">ねっぱん！ (Neppan!)</option>
                 <option value="tl_lincoln">TL-リンカーン (TL-Lincoln)</option>
                 <option value="temairazu">手間いらず (TEMAIRAZU)</option>
                 <option value="beds24">Beds24</option>
                 <option value="tactex">タクトピクセル (TACTEX)</option>
                 <option value="minpaku_in">民泊IN</option>
                 <option value="other">その他 (Webhook連携等)</option>
               </select>
               <label className="block text-sm text-gray-600 mb-1">API Key / Token</label>
               <input type="password" placeholder="****************" className="w-full p-2 border rounded" defaultValue={integrations.site_controller_api_key || ''} />
             </div>

             <div className="border p-4 rounded bg-gray-50">
               <h4 className="font-semibold text-gray-700 mb-2">ダイレクトOTA連携</h4>
               <label className="flex items-center space-x-2 mb-2">
                 <input type="checkbox" defaultChecked={integrations.rakuten_enabled} /> <span>楽天トラベル</span>
               </label>
               <label className="flex items-center space-x-2 mb-2">
                 <input type="checkbox" defaultChecked={integrations.bookingcom_enabled} /> <span>Booking.com</span>
               </label>
               <label className="flex items-center space-x-2">
                 <input type="checkbox" defaultChecked={integrations.airbnb_enabled} /> <span>Airbnb</span>
               </label>
             </div>
           </div>

           <button className="mt-4 bg-gray-800 text-white px-4 py-2 rounded font-bold hover:bg-gray-900">連携テスト＆保存</button>
        </div>
      )}

      {syncStatus && (
        <div className="bg-blue-50 p-4 border border-blue-200 rounded">
          <h3 className="font-bold text-blue-800 text-lg mb-2">価格流し込み・同期ステータス</h3>
          <p className="text-sm text-gray-700 mb-1"><strong>同期モード:</strong> {integrations?.sync_mode === 'daily' ? '1日1回バッチ同期 (Standard)' : integrations?.sync_mode === 'realtime' ? 'リアルタイム同期 (Pro)' : 'AI完全自動・チャネル最適化 (Enterprise)'}</p>
          <p className="text-sm text-gray-700 mb-1"><strong>最終同期日時:</strong> {syncStatus.last_sync_time}</p>
          <p className="text-sm text-gray-700 mb-1"><strong>反映先:</strong> {syncStatus.synced_ota_list.join(", ")}</p>
          <div className="mt-2 p-3 bg-white rounded border border-green-200">
             <p className="text-green-700 font-bold flex items-center"><span className="mr-2">✓</span> {syncStatus.message}</p>
          </div>
        </div>
      )}
    </div>
  );

  const renderDataTab = () => (
    <div className="space-y-4">
      <div className="bg-yellow-50 p-4 border border-yellow-200 rounded">
        <h3 className="font-bold text-yellow-800 mb-2">過去データの取り込み (CSVインポート)</h3>
        <p className="text-sm text-gray-700 mb-4">
          外部の予約台帳や以前のシステムで集計している過去の予約データ（価格、稼働率、日付）をアップロードすることで、AIによる需要予測の精度を高めることができます。
        </p>
        <div className="border-2 border-dashed border-yellow-400 p-8 text-center bg-white rounded cursor-pointer hover:bg-yellow-100 transition-colors">
          <span className="text-3xl mb-2 block">📁</span>
          <p className="text-gray-600 font-bold mb-1">CSVファイルをここにドロップ</p>
          <p className="text-xs text-gray-400">または クリックしてファイルを選択</p>
        </div>
      </div>
    </div>
  );

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden mt-6 mb-8">
      <div className="flex border-b">
        <button className={`flex-1 py-3 font-bold text-sm ${activeTab === 'facility' ? 'bg-gray-50 text-blue-600 border-b-2 border-blue-600' : 'text-gray-500 hover:bg-gray-50'}`} onClick={() => setActiveTab('facility')}>施設基本設定・安全装置</button>
        <button className={`flex-1 py-3 font-bold text-sm ${activeTab === 'integration' ? 'bg-gray-50 text-blue-600 border-b-2 border-blue-600' : 'text-gray-500 hover:bg-gray-50'}`} onClick={() => setActiveTab('integration')}>API連携・同期ステータス</button>
        <button className={`flex-1 py-3 font-bold text-sm ${activeTab === 'data' ? 'bg-gray-50 text-blue-600 border-b-2 border-blue-600' : 'text-gray-500 hover:bg-gray-50'}`} onClick={() => setActiveTab('data')}>過去データアップロード</button>
      </div>
      <div className="p-6">
        {activeTab === 'facility' && renderFacilityTab()}
        {activeTab === 'integration' && renderIntegrationTab()}
        {activeTab === 'data' && renderDataTab()}
      </div>
    </div>
  );
}
