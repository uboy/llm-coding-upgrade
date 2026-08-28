# Лифт "Стрела" (Java)

Task.java: `public static final class Elevator`:
- конструктор Elevator(int floors, int capacity); старт: этаж 1, двери закрыты;
- `void call(int floor)` — добавить цель;
- `void step()` — на 1 этаж к цели (ближайшая; при равенстве - вниз); по достижении цель снимается и двери открываются; ехать с открытыми дверями - IllegalStateException (выбросить при step, если двери открыты);
- `void board(int n)` — двери открыты (иначе IllegalStateException); перегруз - IllegalArgumentException, состав не меняется;
- геттеры: `int current()`, `boolean doorsOpen()`, `int passengers()`.

Целей несколько — step двигает на 1 этаж к ближайшей по расстоянию (при равенстве - к нижней).
