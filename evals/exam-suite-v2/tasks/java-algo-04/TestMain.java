import java.util.List;
public class TestMain {
    static int failures = 0;
    static void check(boolean c, String name) { if (!c) { System.out.println("FAIL " + name); failures++; } }
    public static void main(String[] args) {
        check(java.util.Arrays.equals(Task.minWindow(List.of("a","x","b","y","a","b"), List.of("a","b")), new int[]{4,6}), "basic");
        check(java.util.Arrays.equals(Task.minWindow(List.of("a"), List.of()), new int[]{0,0}), "empty");
        check(Task.minWindow(List.of("a","b"), List.of("a","c")) == null, "no cover");
        check(java.util.Arrays.equals(Task.minWindow(List.of("a","b","a","b"), List.of("a","b")), new int[]{0,2}), "tie");
        check(java.util.Arrays.equals(Task.minWindow(List.of("z","q","z"), List.of("z")), new int[]{0,1}), "single");
        if (failures > 0) { System.out.println(failures + " failures"); System.exit(1); }
        System.out.println("OK");
    }
}
