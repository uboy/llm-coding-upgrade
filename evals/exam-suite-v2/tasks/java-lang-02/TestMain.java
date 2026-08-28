import java.util.Comparator;
import java.util.List;
public class TestMain {
    static int failures = 0;
    static void check(boolean c, String name) { if (!c) { System.out.println("FAIL " + name); failures++; } }
    public static void main(String[] args) {
        check(Task.minOf(List.of(3, 1, 2)).equals(1), "ints");
        check(Task.minOf(List.of("pear", "apple")).equals("apple"), "strings");
        check(Task.minOf(List.of(5)).equals(5), "single");
        check(Task.minOf(List.of(3, 1, 2), Comparator.reverseOrder()).equals(3), "reversed");
        boolean t1 = false; try { Task.<Integer>minOf(java.util.Collections.<Integer>emptyList()); } catch (IllegalArgumentException e) { t1 = true; }
        boolean t2 = false; try { Task.<Integer>minOf(java.util.Collections.<Integer>emptyList(), Comparator.naturalOrder()); } catch (IllegalArgumentException e) { t2 = true; }
        check(t1, "empty nat"); check(t2, "empty cmp");
        if (failures > 0) { System.out.println(failures + " failures"); System.exit(1); }
        System.out.println("OK");
    }
}
