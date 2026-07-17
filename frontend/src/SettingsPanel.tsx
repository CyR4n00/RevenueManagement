import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE = 'http://localhost:8000';

interface SettingsPanelProps {
  onClose: () => void;
}

export function SettingsPanel({ onClose }: SettingsPanelProps) {
  const [competitors, setCompetitors] = useState<any[]>([]);
  const [facility, setFacility] = useState<any>(null);
  const [ranks, setRanks] = useState<any[]>([]);
  const [minPrice, setMinPrice] = useState<number>(5000);
  const [maxPrice, setMaxPrice] = useState<number>(30000);
  const [notifyLine, setNotifyLine] = useState<boolean>(true);
  const [notifyEmail, setNotifyEmail] = useState<boolean>(false);
  const [notifyEmailAddress, setNotifyEmailAddress] = useState<string>('');
  const [notifyThreshold, setNotifyThreshold] = useState<string>('3000');
  const [notifyTiming, setNotifyTiming] = useState<string>('morning');

  useEffect(() => {
    axios.get(`${API_BASE}/config`)
      .then(res => {
        const lineConfig = res.data.find((c: any) => c.key === 'NOTIFY_LINE');
        if (lineConfig) setNotifyLine(lineConfig.value === 'true');

        const emailConfig = res.data.find((c: any) => c.key === 'NOTIFY_EMAIL');
        if (emailConfig) setNotifyEmail(emailConfig.value === 'true');

        const emailAddrConfig = res.data.find((c: any) => c.key === 'NOTIFY_EMAIL_ADDRESS');
        if (emailAddrConfig) setNotifyEmailAddress(emailAddrConfig.value);

        const thresholdConfig = res.data.find((c: any) => c.key === 'NOTIFY_THRESHOLD');
        if (thresholdConfig) setNotifyThreshold(thresholdConfig.value);

        const timingConfig = res.data.find((c: any) => c.key === 'NOTIFY_TIMING');
        if (timingConfig) setNotifyTiming(timingConfig.value);
      })
      .catch(err => console.error("Failed to load config:", err));

    // Load config from backend
    axios.get(`${API_BASE}/competitors`)
      .then(res => {
        if (res.data && res.data.length > 0) {
          setCompetitors(res.data);
        }
      })
      .catch(err => console.error("Failed to load competitors:", err));

    axios.get(`${API_BASE}/facility`)
      .then(res => {
        if (res.data) {
          setFacility(res.data);
          if (res.data.min_price) setMinPrice(res.data.min_price);
          if (res.data.max_price) setMaxPrice(res.data.max_price);
        }
      })
      .catch(err => console.error("Failed to load facility:", err));

    axios.get(`${API_BASE}/ranks`)
      .then(res => {
        if (res.data && res.data.length > 0) {
          setRanks(res.data);
        }
      })
      .catch(err => console.error("Failed to load ranks:", err));
  }, []);

  const handleSave = async () => {
    try {
      await axios.post(`${API_BASE}/ranks`, ranks);
      await axios.post(`${API_BASE}/competitors`, competitors);

      if (facility) {
        await axios.post(`${API_BASE}/facility`, {
          id: facility.id,
          name: facility.name,
          base_price: facility.base_price,
          min_price: minPrice,
          max_price: maxPrice
        });
      }

      const configs = [
        { key: 'NOTIFY_LINE', value: notifyLine.toString() },
        { key: 'NOTIFY_EMAIL', value: notifyEmail.toString() },
        { key: 'NOTIFY_EMAIL_ADDRESS', value: notifyEmailAddress },
        { key: 'NOTIFY_THRESHOLD', value: notifyThreshold },
        { key: 'NOTIFY_TIMING', value: notifyTiming }
      ];

      for (const conf of configs) {
         await axios.post(`${API_BASE}/config`, conf);
      }

      onClose();
    } catch (e) {
      console.error("Failed to save settings", e);
      onClose();
    }
  };

  const handleCompNameChange = (index: number, newName: string) => {
    const updated = [...competitors];
    updated[index] = { ...updated[index], name: newName };
    setCompetitors(updated);
  };

  const handleCompUrlChange = (index: number, newUrl: string) => {
    const updated = [...competitors];
    updated[index] = { ...updated[index], url: newUrl };
    setCompetitors(updated);
  };

  const addCompetitor = () => {
    setCompetitors([...competitors, { id: Date.now(), name: '', url: '' }]);
  };

  const removeCompetitor = (index: number) => {
    const updated = [...competitors];
    updated.splice(index, 1);
    setCompetitors(updated);
  };

  const handleRankNameChange = (index: number, newName: string) => {
    const updated = [...ranks];
    updated[index] = { ...updated[index], name: newName };
    setRanks(updated);
  };

  const handleRankPriceChange = (index: number, newPrice: number) => {
    const updated = [...ranks];
    updated[index] = { ...updated[index], price: newPrice };
    setRanks(updated);
  };

  const addRank = () => {
    setRanks([...ranks, { name: '新規プラン', price: 0 }]);
  };

  const removeRank = (index: number) => {
    const updated = [...ranks];
    updated.splice(index, 1);
    setRanks(updated);
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden mt-6 mb-8">
      <div className="bg-gray-50 border-b p-4 flex justify-between items-center">
        <div>
          <h2 className="font-bold text-lg text-gray-800">⚙️ アシスタント設定 (ベンチマーク・通知)</h2>
          <p className="text-xs text-gray-500 mt-1">AIが毎日監視する競合施設と、アラートの通知先を設定します。</p>
        </div>
        <button aria-label="閉じる" onClick={onClose} className="text-gray-500 hover:text-gray-800 font-bold text-xl focus-visible:ring-2 focus-visible:outline-none rounded">&times;</button>
      </div>

      <div className="p-6 space-y-8">
        {/* Competitor Settings */}
        <div>
          <h3 className="font-bold text-gray-700 mb-4 border-b pb-2">1. ベンチマーク（競合）登録</h3>
          <div className="flex justify-between items-center mb-3">
             <div />
             <button
                onClick={addCompetitor}
                className="bg-blue-100 text-blue-700 text-xs px-3 py-1 rounded font-bold hover:bg-blue-200 transition-colors"
             >
                + 競合を追加
             </button>
          </div>
          <div className="space-y-4">
            {competitors.map((comp, index) => (
              <div key={comp.id || index} className="border rounded-lg p-4 bg-gray-50 flex flex-col md:flex-row items-start md:items-center space-y-3 md:space-y-0 md:space-x-4 relative">
                 <div className="bg-blue-100 text-blue-800 font-bold w-8 h-8 rounded-full flex items-center justify-center shrink-0">
                   {index + 1}
                 </div>
                 <div className="flex-1 w-full">
                   <label htmlFor={`comp-name-${index}`} className="block text-xs font-bold text-gray-500 mb-1">施設名 (表示用)</label>
                   <input id={`comp-name-${index}`} type="text" className="w-full p-2 border rounded text-sm focus:ring-2 focus:ring-blue-400 outline-none" value={comp.name} onChange={(e) => handleCompNameChange(index, e.target.value)} />
                 </div>
                 <div className="flex-2 w-full md:w-1/2">
                   <label htmlFor={`comp-url-${index}`} className="block text-xs font-bold text-gray-500 mb-1">OTAのURL (楽天トラベル, Booking.com等)</label>
                   <input id={`comp-url-${index}`} type="text" className="w-full p-2 border rounded text-sm focus:ring-2 focus:ring-blue-400 outline-none" value={comp.url || ''} onChange={(e) => handleCompUrlChange(index, e.target.value)} />
                 </div>
                 <button
                    onClick={() => removeCompetitor(index)}
                    aria-label="この競合を削除"
                    className="absolute top-2 right-2 md:static text-gray-400 hover:text-red-500 transition-colors p-2"
                  >
                    🗑️
                  </button>
              </div>
            ))}
            {competitors.length === 0 && (
              <div className="text-sm text-gray-500 p-4 border rounded bg-white text-center">
                登録されている競合施設がありません。
              </div>
            )}
          </div>
          <div className="mt-4 text-xs text-gray-500 flex items-start bg-gray-50 p-3 rounded border">
            <span className="mr-2">ℹ️</span>
            <p>※現在は直感的な把握を優先し「対象施設のその日の最安値（Best Available Rate）」を基準に比較します。将来のアップデートにて「部屋タイプ」や「食事有無」を指定した厳密なプラン比較が可能になる予定です。</p>
          </div>
        </div>

        {/* Guardrails (Min/Max Price) Settings */}
        <div>
          <div className="flex items-center justify-between border-b pb-2 mb-4">
            <h3 className="font-bold text-gray-700">2. 自社プラン・価格ガードレール設定</h3>
            <span className="bg-red-100 text-red-800 text-[10px] px-2 py-1 rounded font-bold">必須設定</span>
          </div>
          <p className="text-sm text-gray-600 mb-4">
            AIが極端な値下げや非現実的な値上げを提案しないよう、自社ホテルの価格の「下限」と「上限」を設定します。また、料金ランクごとのしきい値を設定することで、自社に最適な価格提案を受けられます。
          </p>
          <div className="flex space-x-4 mb-4">
            <div className="flex-1">
              <label htmlFor="min_price" className="block text-xs font-bold text-gray-500 mb-1">最低販売価格（下限）</label>
              <div className="relative">
                <span className="absolute left-3 top-2 text-gray-500">¥</span>
                <input id="min_price" type="number" value={minPrice} onChange={(e) => setMinPrice(Number(e.target.value))} className="w-full pl-8 p-2 border rounded text-sm focus:ring-2 focus:ring-blue-400 outline-none" />
              </div>
            </div>
            <div className="flex-1">
              <label htmlFor="max_price" className="block text-xs font-bold text-gray-500 mb-1">最高販売価格（上限）</label>
              <div className="relative">
                <span className="absolute left-3 top-2 text-gray-500">¥</span>
                <input id="max_price" type="number" value={maxPrice} onChange={(e) => setMaxPrice(Number(e.target.value))} className="w-full pl-8 p-2 border rounded text-sm focus:ring-2 focus:ring-blue-400 outline-none" />
              </div>
            </div>
          </div>

          <div className="bg-gray-50 p-4 rounded border mt-4">
            <div className="flex justify-between items-center mb-3">
              <h4 className="text-sm font-bold text-gray-700">料金ランク（プラン）しきい値設定</h4>
              <button
                onClick={addRank}
                className="bg-blue-100 text-blue-700 text-xs px-3 py-1 rounded font-bold hover:bg-blue-200 transition-colors"
              >
                + ランクを追加
              </button>
            </div>

            <div className="space-y-3">
              {ranks.map((rank, index) => (
                <div key={index} className="flex items-center space-x-3 bg-white p-3 rounded border">
                  <div className="flex-1">
                    <label htmlFor={`rank_name_${index}`} className="sr-only">ランク名</label>
                    <input
                      id={`rank_name_${index}`}
                      type="text"
                      value={rank.name}
                      onChange={(e) => handleRankNameChange(index, e.target.value)}
                      className="w-full p-2 border rounded text-sm focus:ring-2 focus:ring-blue-400 outline-none"
                      placeholder="ランク A"
                    />
                  </div>
                  <div className="flex-1">
                    <label htmlFor={`rank_price_${index}`} className="sr-only">しきい値価格</label>
                    <div className="relative">
                      <span className="absolute left-3 top-2 text-gray-500">¥</span>
                      <input
                        id={`rank_price_${index}`}
                        type="number"
                        value={rank.price}
                        onChange={(e) => handleRankPriceChange(index, parseInt(e.target.value) || 0)}
                        className="w-full pl-8 p-2 border rounded text-sm focus:ring-2 focus:ring-blue-400 outline-none"
                      />
                    </div>
                  </div>
                  <button
                    onClick={() => removeRank(index)}
                    aria-label="このランクを削除"
                    className="text-gray-400 hover:text-red-500 transition-colors p-2"
                  >
                    🗑️
                  </button>
                </div>
              ))}
              {ranks.length === 0 && (
                <p className="text-sm text-gray-500 text-center py-4">料金ランクが設定されていません。</p>
              )}
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
               <label htmlFor="notify-line" className="flex items-center space-x-2 text-sm text-gray-700 mb-2">
                 <input id="notify-line" type="checkbox" checked={notifyLine} onChange={(e) => setNotifyLine(e.target.checked)} className="rounded text-green-600 focus:ring-green-500" />
                 <span>LINEで通知を受け取る</span>
               </label>
               <button className="w-full bg-[#06C755] text-white font-bold py-2 rounded shadow hover:bg-green-600 transition-colors text-sm mt-2 focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-green-500 focus-visible:outline-none">
                 LINEアカウントと連携する
               </button>
            </div>

            <div className="border p-4 rounded-lg bg-gray-50">
               <h4 className="font-bold text-gray-700 flex items-center mb-3">
                 <span className="mr-2">📧</span> メール通知
               </h4>
               <label htmlFor="notify-email" className="flex items-center space-x-2 text-sm text-gray-700 mb-2">
                 <input id="notify-email" type="checkbox" checked={notifyEmail} onChange={(e) => setNotifyEmail(e.target.checked)} className="rounded text-blue-600 focus:ring-blue-500" />
                 <span>メールで通知を受け取る</span>
               </label>
               <label htmlFor="email-input" className="sr-only">メールアドレス</label>
               <input id="email-input" type="email" value={notifyEmailAddress} onChange={(e) => setNotifyEmailAddress(e.target.value)} placeholder="example@hotel.com" className="w-full p-2 border rounded text-sm focus:ring-2 focus:ring-blue-400 outline-none mt-1" />
            </div>
          </div>

          {/* Advanced Notification Filters */}
          <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
             <h4 className="text-sm font-bold text-gray-700 mb-3">通知の頻度と条件（スパム防止）</h4>
             <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
               <div>
                 <label htmlFor="threshold-select" className="block text-xs font-bold text-gray-500 mb-1">通知を送る「価格変動」のしきい値</label>
                 <select id="threshold-select" value={notifyThreshold} onChange={(e) => setNotifyThreshold(e.target.value)} className="w-full p-2 border rounded text-sm focus:ring-2 focus:ring-blue-400 outline-none bg-white">
                   <option value="1000">1,000円以上の変動で通知</option>
                   <option value="3000">3,000円以上の変動で通知 (推奨)</option>
                   <option value="5000">5,000円以上の変動で通知</option>
                 </select>
               </div>
               <div>
                 <label htmlFor="timing-select" className="block text-xs font-bold text-gray-500 mb-1">通知のタイミング</label>
                 <select id="timing-select" value={notifyTiming} onChange={(e) => setNotifyTiming(e.target.value)} className="w-full p-2 border rounded text-sm focus:ring-2 focus:ring-blue-400 outline-none bg-white">
                   <option value="immediate">変動を検知したら即時</option>
                   <option value="morning">1日1回 朝10時にまとめて通知 (推奨)</option>
                   <option value="evening">1日1回 夕方17時にまとめて通知</option>
                 </select>
               </div>
             </div>
          </div>
        </div>

        <div className="flex justify-end pt-4 border-t">
          <button onClick={handleSave} className="bg-blue-600 text-white px-6 py-2 rounded-lg font-bold shadow hover:bg-blue-700 transition-colors focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-blue-500 focus-visible:outline-none">
            設定を保存して戻る
          </button>
        </div>
      </div>
    </div>
  );
}
