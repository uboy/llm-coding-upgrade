import java.util.List;
import java.util.Map;
public class TestMain {
    static int failures = 0;
    @SuppressWarnings("unchecked")
    static void check(boolean c, String name) { if (!c) { System.out.println("FAIL " + name); failures++; } }
    public static void main(String[] args) {
        Map<String, Object> r = Task.process(List.of("01.01.2024|cash|C|100", "02.01.2024|cash|D|30"));
        check(((Map<String, Long>) r.get("balances")).equals(Map.of("cash", 70L)), "dc");
        check(((List<String>) r.get("skipped")).isEmpty(), "no skip");
        r = Task.process(List.of("32.01.2024|a|C|1", "01.01.2024|a|X|1", "01.01.2024|a|C|-1", "01.01.2024|a|C|1.5", "broken"));
        check(((Map<String, Long>) r.get("balances")).isEmpty(), "all skipped");
        check(((List<String>) r.get("skipped")).size() == 5, "skip count");
        r = Task.process(List.of("29.02.2024|a|C|1", "29.02.2023|b|C|1"));
        check(((Map<String, Long>) r.get("balances")).equals(Map.of("a", 1L)), "leap");
        if (failures > 0) { System.out.println(failures + " failures"); System.exit(1); }
        System.out.println("OK");
    }
}
