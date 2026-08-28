# Свободный слот мастерской (Java)

Напиши класс `Task` (файл Task.java, пакет по умолчанию) со статическим методом:

`public static int[] firstFreeSlot(int[][] busy, int duration, int dayStart, int dayEnd)`

busy — массив пар {start, end} (полуоткрытые; пересечения и любой порядок допустимы; нулевая длина не считается занятостью). Вернуть самый ранний {t, t+duration}, целиком свободный внутри [dayStart, dayEnd], или null. duration <= 0 — IllegalArgumentException.
