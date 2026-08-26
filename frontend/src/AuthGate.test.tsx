import { authErrorMessage } from './AuthGate';

test('translates the Supabase email cooldown message', () => {
  expect(authErrorMessage('For security purposes, you can only request this after 54 seconds.'))
    .toBe('セキュリティ保護のため、あと54秒待ってから再度お試しください。');
});

test('translates common login errors', () => {
  expect(authErrorMessage('Invalid login credentials'))
    .toBe('メールアドレスまたはパスワードが正しくありません。');
  expect(authErrorMessage('Email not confirmed'))
    .toBe('メールアドレスの確認が完了していません。確認メール内のリンクを押してください。');
});
