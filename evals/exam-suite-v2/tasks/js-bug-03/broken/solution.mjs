const MONTHS = ["январь","февраль","март","апрель","май","июнь","июль","август","сентябрь","октябрь","ноябрь","декабрь"];

export function monthName(isoDate) {
  const d = new Date(isoDate);
  return MONTHS[d.getMonth()];
}
