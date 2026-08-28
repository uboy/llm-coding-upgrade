# try-with-resources "Реквизит" (Java)

Task.java: `public static final class Ledger implements AutoCloseable`:
- конструктор `Ledger(Appendable out)`; `add(String)` накапливает в буфер, пока открыт; после close - IllegalStateException;
- `close()` — только помечает закрытие (ничего в out не пишет); повторный close - IllegalStateException;
- `commit()` — сброс накопленного в out ОДНИМ вызовом append (допустим только после close, иначе IllegalStateException); повторный commit - IllegalStateException.

Статический хелпер `public static String transcribe(Appendable out, boolean failMidway)` обязан использовать try-with-resources: пишет "a","b"; при failMidway бросает RuntimeException (накопленное в out НЕ попадает); при успехе делает commit и возвращает out.toString(). При исключении накопленное не сбрасывать (верни/брось как получится — главное тест).
