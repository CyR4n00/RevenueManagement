import React, { useState } from 'react';
import axios from 'axios';

interface Rule {
  id: number;
  facility_id: number;
  occupancy_threshold_percent: number;
  price_multiplier: number;
  active: boolean;
}

interface RulesConfigProps {
  rules: Rule[];
  facilityId: number;
  onRuleChanged: () => void;
}

export function RulesConfig({ rules, facilityId, onRuleChanged }: RulesConfigProps) {
  const [newThreshold, setNewThreshold] = useState(80);
  const [newMultiplier, setNewMultiplier] = useState(1.2);
  const [isAdding, setIsAdding] = useState(false);

  const toggleRule = async (ruleId: number) => {
    try {
      await axios.put(`http://localhost:8000/rules/${ruleId}/toggle`);
      onRuleChanged();
    } catch (error) {
       console.error("ルールの変更に失敗しました:", error);
    }
  }

  const deleteRule = async (ruleId: number) => {
    try {
      await axios.delete(`http://localhost:8000/rules/${ruleId}`);
      onRuleChanged();
    } catch (error) {
       console.error("ルールの削除に失敗しました:", error);
    }
  }

  const addRule = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await axios.post('http://localhost:8000/rules', {
        facility_id: facilityId,
        occupancy_threshold_percent: newThreshold / 100.0,
        price_multiplier: newMultiplier,
        active: true
      });
      setIsAdding(false);
      onRuleChanged();
    } catch (error) {
      console.error("ルールの追加に失敗しました:", error);
    }
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden flex flex-col h-full">
      <div className="bg-gray-50 p-4 border-b flex justify-between items-center">
        <div>
            <h2 className="text-lg font-bold text-gray-800">価格変動ルール (カスタム設定)</h2>
            <p className="text-xs text-gray-500 mt-1">オーナー様自身でしきい値や倍率を自由に設定できます</p>
        </div>
        {!isAdding && (
            <button
              onClick={() => setIsAdding(true)}
              className="bg-blue-600 text-white text-xs font-bold px-3 py-1.5 rounded hover:bg-blue-700"
            >
              ＋ 新規ルール追加
            </button>
        )}
      </div>

      <div className="p-4 space-y-3 flex-grow overflow-y-auto max-h-[400px]">
        {isAdding && (
            <form onSubmit={addRule} className="bg-blue-50 p-3 rounded-lg border border-blue-200 mb-4">
                <h4 className="text-sm font-bold text-blue-800 mb-2">新しいルールを作成</h4>
                <div className="flex items-center space-x-2 text-sm text-gray-700 mb-3">
                    <span>稼働率が</span>
                    <input type="number" min="1" max="100" className="w-16 p-1 border rounded text-center font-bold" value={newThreshold} onChange={e => setNewThreshold(Number(e.target.value))} required />
                    <span>% 以上の場合、価格を</span>
                    <input type="number" min="0.1" max="5.0" step="0.1" className="w-16 p-1 border rounded text-center font-bold" value={newMultiplier} onChange={e => setNewMultiplier(Number(e.target.value))} required />
                    <span>倍にする</span>
                </div>
                <div className="flex space-x-2">
                    <button type="submit" className="bg-blue-600 text-white text-xs px-3 py-1.5 rounded font-bold">追加する</button>
                    <button type="button" onClick={() => setIsAdding(false)} className="bg-gray-300 text-gray-700 text-xs px-3 py-1.5 rounded font-bold">キャンセル</button>
                </div>
            </form>
        )}

        {rules.length > 0 ? rules.map(rule => (
            <div key={rule.id} className={`flex items-center justify-between p-3 rounded-lg border ${rule.active ? 'bg-white border-gray-200 shadow-sm' : 'bg-gray-50 border-gray-100 opacity-60'}`}>
                <div>
                  <p className={`text-sm font-medium ${rule.active ? 'text-gray-800' : 'text-gray-500'}`}>
                    稼働率が <span className="font-bold text-lg">{Math.round(rule.occupancy_threshold_percent * 100)}%</span> 以上の場合
                  </p>
                  <p className={`text-sm mt-1 font-bold ${rule.active ? 'text-blue-600' : 'text-gray-500'}`}>
                    基本価格を <span className="text-lg">{rule.price_multiplier}</span> 倍 にする
                  </p>
                </div>
                <div className="flex flex-col space-y-2 items-end">
                    <button
                      onClick={() => toggleRule(rule.id)}
                      className={`w-16 py-1 rounded text-xs font-bold transition-colors ${
                        rule.active
                          ? 'bg-green-100 text-green-700 border border-green-300 hover:bg-green-200'
                          : 'bg-gray-200 text-gray-500 border border-gray-300 hover:bg-gray-300'
                      }`}
                    >
                      {rule.active ? '稼働中' : '停止中'}
                    </button>
                    <button
                      onClick={() => deleteRule(rule.id)}
                      className="text-[10px] text-red-500 hover:text-red-700 underline"
                    >
                      削除
                    </button>
                </div>
            </div>
        )) : (
          <p className="text-sm text-gray-500 text-center py-4">ルールが設定されていません</p>
        )}
      </div>
    </div>
  );
}
