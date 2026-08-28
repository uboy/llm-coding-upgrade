public class TestMain {
    static int failures = 0;
    static void check(boolean c, String name) { if (!c) { System.out.println("FAIL " + name); failures++; } }
    public static void main(String[] args) {
        check(Task.calc("light", 10) == 0, "in");
        check(Task.calc("light", 40) == 1500, "light over");
        check(Task.calc("standard", 150) == 5000, "std");
        check(Task.calc("premium", 400) == 8000, "premium");
        boolean threw = false;
        try { Task.calc("ultra", 10); } catch (IllegalArgumentException e) { threw = true; }
        check(threw, "unknown");
        if (failures > 0) { System.out.println(failures + " failures"); System.exit(1); }
        System.out.println("OK");
    }
}
