public class TestMain {
    static int failures = 0;
    static void check(boolean c, String name) { if (!c) { System.out.println("FAIL " + name); failures++; } }
    public static void main(String[] args) {
        Task.TokenBucket b = new Task.TokenBucket(2, 5);
        check(b.tokens() == 5, "start");
        Task.TokenBucket c = new Task.TokenBucket(2, 3);
        check(c.allow(1) && c.allow(1) && c.allow(1) && !c.allow(1), "drain");
        Task.TokenBucket d = new Task.TokenBucket(5, 4);
        d.allow(4); d.tick(); d.tick();
        check(d.tokens() == 4, "cap");
        boolean threw = false;
        try { new Task.TokenBucket(1, 5).allow(0); } catch (IllegalArgumentException e) { threw = true; }
        check(threw, "bad cost");
        if (failures > 0) { System.out.println(failures + " failures"); System.exit(1); }
        System.out.println("OK");
    }
}
