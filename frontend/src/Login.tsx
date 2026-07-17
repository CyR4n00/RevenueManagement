import React, { useState } from 'react';
import axios from 'axios';

const API_BASE = 'http://localhost:8000';

interface LoginProps {
  onLoginSuccess: () => void;
}

export function Login({ onLoginSuccess }: LoginProps) {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');

    try {
      const response = await axios.post(`${API_BASE}/create-checkout-session`, {
        email: email
      });

      if (response.data.url) {
         window.location.href = response.data.url;
      } else {
         setMessage("決済画面への遷移に失敗しました。");
      }
    } catch (err) {
      console.error(err);
      setMessage("エラーが発生しました。");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-xl shadow-md p-8">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-gray-800">レベニューアシスタント</h1>
          <p className="text-sm text-gray-500 mt-2">アカウントを作成して利用を開始する</p>
        </div>

        {message && (
          <div className="bg-red-50 text-red-600 p-3 rounded mb-4 text-sm">
            {message}
          </div>
        )}

        <form onSubmit={handleSignup} className="space-y-6">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">メールアドレス</label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full p-3 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 outline-none"
              placeholder="you@example.com"
            />
          </div>

          <button
            type="submit"
            disabled={loading || !email}
            className="w-full bg-blue-600 text-white font-bold py-3 rounded shadow hover:bg-blue-700 transition-colors disabled:opacity-50"
          >
            {loading ? '準備中...' : 'クレジットカードを登録して開始 (月額プラン)'}
          </button>
        </form>

        <div className="mt-6 border-t pt-4 text-center">
            <button
                onClick={onLoginSuccess}
                className="text-sm text-gray-500 hover:text-gray-800 underline"
            >
                [開発用] 決済をスキップしてログイン
            </button>
        </div>
      </div>
    </div>
  );
}
