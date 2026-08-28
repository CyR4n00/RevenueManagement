import { checkOtaPropertyUrl } from './OtaUrlHelp';

test('accepts Jalan and Rakuten property URLs', () => {
  expect(checkOtaPropertyUrl('https://www.jalan.net/yad315667/plan/?vos=test').valid).toBe(true);
  expect(checkOtaPropertyUrl('https://travel.rakuten.co.jp/HOTEL/14138/14138.html').valid).toBe(true);
});

test('rejects search and non-property URLs with Japanese guidance', () => {
  const result = checkOtaPropertyUrl('https://www.jalan.net/kankou/');
  expect(result.valid).toBe(false);
  expect(result.message).toContain('/yad＋数字');
  expect(checkOtaPropertyUrl('https://www.google.com/search?q=hotel').valid).toBe(false);
});
