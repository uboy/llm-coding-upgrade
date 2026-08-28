import java.util.List;
public class TestMain {
    static int failures = 0;
    static void check(boolean c, String name) { if (!c) { System.out.println("FAIL " + name); failures++; } }
    public static void main(String[] args) {
        check(Task.sameOrder(5, 5), "small");
        check(!Task.sameOrder(5, 6), "small ne");
        check(Task.sameOrder(1000, 1000), "big eq");
        check(Task.sameOrder(128, 128), "boundary");
        check(Task.countMatches(List.of(900, 901, 900), 900) == 2, "count");
        check(Task.countMatches(List.of(200, 200), 300) == 0, "count none");
        if (failures > 0) { System.out.println(failures + " failures"); System.exit(1); }
        System.out.println("OK");
    }
}
