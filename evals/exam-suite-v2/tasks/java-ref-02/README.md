# Рефактор: тарифы "Гиря" (Java)

Task.java: `public static long calc(String plan, long minutes)` - копейки; light: 30 мин вкл, 150 коп/мин; standard: 100, 100; premium: 300, 80. Округление вниз. Неизвестный план - IllegalArgumentException.

Лесенка switch - отрефактори на статическую Map<String, long[]> {included, perMinuteKop}, сохранив API и поведение.
