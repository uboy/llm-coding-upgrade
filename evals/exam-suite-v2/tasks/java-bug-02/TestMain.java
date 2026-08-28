public class TestMain {
    static int failures = 0;
    static void check(boolean c, String name) { if (!c) { System.out.println("FAIL " + name); failures++; } }
    public static void main(String[] args) {
        check(Task.countOverlapping("aaa", "aa") == 2, "overlap");
        check(Task.countOverlapping("abab", "ab") == 2, "abab");
        check(Task.countOverlapping("abc", "z") == 0, "none");
        check(Task.countOverlapping("x", "") == 0, "empty needle");
        check(Task.countOverlapping("aaaa", "aa") == 3, "aaaa");
        if (failures > 0) { System.out.println(failures + " failures"); System.exit(1); }
        System.out.println("OK");
    }
}
