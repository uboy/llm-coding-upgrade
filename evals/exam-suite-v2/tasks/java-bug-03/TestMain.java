public class TestMain {
    static int failures = 0;
    static void check(boolean c, String name) { if (!c) { System.out.println("FAIL " + name); failures++; } }
    public static void main(String[] args) {
        check(Task.monthName("2024-03-09").equals("март"), "march");
        check(Task.monthName("2024-01-31").equals("январь"), "january");
        check(Task.monthName("2024-12-01").equals("декабрь"), "december");
        boolean t1 = false; try { Task.monthName("2024-13-01"); } catch (IllegalArgumentException e) { t1 = true; }
        boolean t2 = false; try { Task.monthName("2024-02-30"); } catch (IllegalArgumentException e) { t2 = true; }
        check(t1, "bad month"); check(t2, "bad day");
        if (failures > 0) { System.out.println(failures + " failures"); System.exit(1); }
        System.out.println("OK");
    }
}
