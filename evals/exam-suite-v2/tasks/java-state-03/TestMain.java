public class TestMain {
    static int failures = 0;
    static void check(boolean c, String name) { if (!c) { System.out.println("FAIL " + name); failures++; } }
    public static void main(String[] args) {
        Task.Elevator e = new Task.Elevator(10, 4);
        e.call(3); e.step(); e.step();
        check(e.current() == 3 && e.doorsOpen(), "arrive open");
        boolean t1 = false;
        try { e.step(); } catch (IllegalStateException ex) { t1 = true; }
        check(t1, "open move");
        Task.Elevator b = new Task.Elevator(10, 2);
        b.call(1); b.step();
        b.board(2);
        boolean t2 = false;
        try { b.board(1); } catch (IllegalArgumentException ex) { t2 = true; }
        check(t2 && b.passengers() == 2, "overload");
        Task.Elevator c = new Task.Elevator(10, 2);
        boolean t3 = false;
        try { c.board(1); } catch (IllegalStateException ex) { t3 = true; }
        check(t3, "closed board");
        Task.Elevator d = new Task.Elevator(10, 2);
        d.step();
        check(d.current() == 1, "idle stay");
        if (failures > 0) { System.out.println(failures + " failures"); System.exit(1); }
        System.out.println("OK");
    }
}
