import { useEffect, useState } from 'react';

export const CALENDAR_TIME_ZONE = 'Asia/Seoul';
export const CALENDAR_WEEKDAYS = ['일', '월', '화', '수', '목', '금', '토'] as const;
const seoulDateFormat = new Intl.DateTimeFormat('en-US', { timeZone: CALENDAR_TIME_ZONE, year: 'numeric', month: '2-digit', day: '2-digit' });

// Calendar display dates are civil dates. Original metadata and stored timestamps stay intact.
export function seoulToday(now: Date = new Date()): string {
  const parts = seoulDateFormat.formatToParts(now);
  const get = (type: string) => parts.find(part => part.type === type)!.value;
  return `${get('year')}-${get('month')}-${get('day')}`;
}

export function isCalendarDay(value: unknown): value is string {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const parsed = new Date(value + 'T00:00:00Z');
  return Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value;
}

export function addCalendarDays(day: string, amount: number): string {
  if (!isCalendarDay(day) || !Number.isInteger(amount)) throw new RangeError('Invalid calendar date');
  const date = new Date(day + 'T00:00:00Z');
  date.setUTCDate(date.getUTCDate() + amount);
  return date.toISOString().slice(0, 10);
}

export function weekStartSunday(day: string): string {
  if (!isCalendarDay(day)) throw new RangeError('Invalid calendar date');
  return addCalendarDays(day, -new Date(day + 'T00:00:00Z').getUTCDay());
}

export function sundayCalendarDays(year: number, zeroMonth: number): string[] {
  const first = new Date(Date.UTC(year, zeroMonth, 1));
  const shift = first.getUTCDay();
  const count = new Date(Date.UTC(year, zeroMonth + 1, 0)).getUTCDate();
  const slots = Math.max(35, Math.ceil((shift + count) / 7) * 7);
  return Array.from({ length: slots }, (_, index) => new Date(Date.UTC(year, zeroMonth, 1 - shift + index)).toISOString().slice(0, 10));
}

export function shiftCalendarMonth(day: string, amount: number): string {
  if (!isCalendarDay(day) || !Number.isInteger(amount)) throw new RangeError('Invalid calendar date');
  const [year, month, number] = day.split('-').map(Number);
  const target = new Date(Date.UTC(year, month - 1 + amount, 1));
  const last = new Date(Date.UTC(target.getUTCFullYear(), target.getUTCMonth() + 1, 0)).getUTCDate();
  target.setUTCDate(Math.min(number, last));
  return target.toISOString().slice(0, 10);
}

export function millisecondsUntilSeoulMidnight(now: Date = new Date()): number {
  const tomorrow = addCalendarDays(seoulToday(now), 1);
  const [year, month, day] = tomorrow.split('-').map(Number);
  return Date.UTC(year, month - 1, day, -9) - now.getTime();
}

export function useSeoulToday(): string {
  const [today, setToday] = useState(() => seoulToday());
  useEffect(() => {
    let timer = 0;
    const update = () => {
      window.clearTimeout(timer);
      const now = new Date();
      setToday(seoulToday(now));
      timer = window.setTimeout(update, Math.max(1, Math.min(millisecondsUntilSeoulMidnight(now) + 25, 60_000)));
    };
    update();
    const resume = () => { if (!document.hidden) update(); };
    document.addEventListener('visibilitychange', resume);
    window.addEventListener('focus', update);
    window.addEventListener('pageshow', update);
    return () => {
      window.clearTimeout(timer);
      document.removeEventListener('visibilitychange', resume);
      window.removeEventListener('focus', update);
      window.removeEventListener('pageshow', update);
    };
  }, []);
  return today;
}
