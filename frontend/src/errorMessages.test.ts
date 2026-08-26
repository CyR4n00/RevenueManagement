import { userFacingErrorMessage } from './errorMessages';

test('known API messages are translated into Japanese', () => {
  const error = { response: { data: { detail: 'This competitor URL is already registered' } } };
  expect(userFacingErrorMessage(error, '失敗しました。')).toBe('この競合施設のURLはすでに登録されています。');
});

test('unknown English details do not leak into the customer screen', () => {
  expect(userFacingErrorMessage(new Error('Unexpected internal failure'), '処理に失敗しました。')).toBe('処理に失敗しました。');
});

test('Japanese server guidance is kept as-is', () => {
  expect(userFacingErrorMessage('入力内容を確認してください。', '失敗しました。')).toBe('入力内容を確認してください。');
});
