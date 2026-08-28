import java.util.List;
public class TestMain {
    static int failures = 0;
    static void check(boolean c, String name) { if (!c) { System.out.println("FAIL " + name); failures++; } }
    public static void main(String[] args) {
        check(Task.validNumbers(List.of("G123-45")).equals(List.of("G123-45")), "ok");
        check(Task.validNumbers(List.of("X1-2", "G1", "G1-")).isEmpty(), "format");
        check(Task.validNumbers(List.of("G123-01")).isEmpty(), "group0");
        check(Task.validNumbers(List.of("g1-2")).isEmpty(), "lowercase");
        check(Task.validNumbers(List.of("G12-3", "bad", "G123456-78901")).equals(List.of("G12-3")), "mixed");
        if (failures > 0) { System.out.println(failures + " failures"); System.exit(1); }
        System.out.println("OK");
    }
}
