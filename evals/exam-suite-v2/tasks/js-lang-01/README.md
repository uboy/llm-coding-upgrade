# Прокси-объект "Ревизор"

Экспортируй `makeAudited(target, onChange)`: возвращает Proxy вокруг target (плоский объект):
- запись свойства (в т.ч. нового) — значение пишется в target и вызывается onChange(key, oldValue, newValue) (старое = undefined для нового ключа);
- удаление свойства (delete) — onChange(key, oldValue, undefined);
- чтение/перечисление (get/ownKeys/…) — как у обычного объекта;
- попытка записать то же значение (===) — onChange НЕ вызывается.

Используй Proxy (new Proxy) — это условие задачи.
