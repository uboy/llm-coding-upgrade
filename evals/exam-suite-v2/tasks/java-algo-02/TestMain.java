public class TestMain {
    static int failures = 0;
    static void check(boolean c, String name) { if (!c) { System.out.println("FAIL " + name); failures++; } }
    public static void main(String[] args) {
        check(Task.decodeBeacon("3a2b#5").equals("aaabb"), "basic");
        check(Task.decodeBeacon("3a!#4").equals("aaaa"), "bang");
        check(Task.decodeBeacon("12x#12").equals("x".repeat(12)), "multidigit");
        check(Task.decodeBeacon("1a!!#3").equals("aaa"), "multi bang");
        boolean t1 = false; try { Task.decodeBeacon("3a"); } catch (IllegalArgumentException e) { t1 = true; }
        boolean t2 = false; try { Task.decodeBeacon("3a#4"); } catch (IllegalArgumentException e) { t2 = true; }
        check(t1, "no cs"); check(t2, "bad cs");
        if (failures > 0) { System.out.println(failures + " failures"); System.exit(1); }
        System.out.println("OK");
    }
}
