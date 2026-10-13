// 원본 순수 함수에서 생성. React hook 제외. dashboard/build-example.mjs 참조.
export const CALENDAR_TIME_ZONE = 'Asia/Seoul';
export const CALENDAR_WEEKDAYS = ['일', '월', '화', '수', '목', '금', '토'];
const seoulDateFormat = new Intl.DateTimeFormat('en-US', { timeZone: CALENDAR_TIME_ZONE, year: 'numeric', month: '2-digit', day: '2-digit' });
// Calendar display dates are civil dates. Original metadata and stored timestamps stay intact.
export function seoulToday(now = new Date()) {
    const parts = seoulDateFormat.formatToParts(now);
    const get = (type) => parts.find(part => part.type === type).value;
    return `${get('year')}-${get('month')}-${get('day')}`;
}
export function isCalendarDay(value) {
    if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value))
        return false;
    const parsed = new Date(value + 'T00:00:00Z');
    return Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value;
}
export function addCalendarDays(day, amount) {
    if (!isCalendarDay(day) || !Number.isInteger(amount))
        throw new RangeError('Invalid calendar date');
    const date = new Date(day + 'T00:00:00Z');
    date.setUTCDate(date.getUTCDate() + amount);
    return date.toISOString().slice(0, 10);
}
export function weekStartSunday(day) {
    if (!isCalendarDay(day))
        throw new RangeError('Invalid calendar date');
    return addCalendarDays(day, -new Date(day + 'T00:00:00Z').getUTCDay());
}
export function sundayCalendarDays(year, zeroMonth) {
    const first = new Date(Date.UTC(year, zeroMonth, 1));
    const shift = first.getUTCDay();
    const count = new Date(Date.UTC(year, zeroMonth + 1, 0)).getUTCDate();
    const slots = Math.max(35, Math.ceil((shift + count) / 7) * 7);
    return Array.from({ length: slots }, (_, index) => new Date(Date.UTC(year, zeroMonth, 1 - shift + index)).toISOString().slice(0, 10));
}
export function shiftCalendarMonth(day, amount) {
    if (!isCalendarDay(day) || !Number.isInteger(amount))
        throw new RangeError('Invalid calendar date');
    const [year, month, number] = day.split('-').map(Number);
    const target = new Date(Date.UTC(year, month - 1 + amount, 1));
    const last = new Date(Date.UTC(target.getUTCFullYear(), target.getUTCMonth() + 1, 0)).getUTCDate();
    target.setUTCDate(Math.min(number, last));
    return target.toISOString().slice(0, 10);
}
export function millisecondsUntilSeoulMidnight(now = new Date()) {
    const tomorrow = addCalendarDays(seoulToday(now), 1);
    const [year, month, day] = tomorrow.split('-').map(Number);
    return Date.UTC(year, month - 1, day, -9) - now.getTime();
}
