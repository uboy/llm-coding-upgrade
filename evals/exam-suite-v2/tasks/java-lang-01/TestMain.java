public class TestMain {
    static int failures = 0;
    static void check(boolean c, String name) { if (!c) { System.out.println("FAIL " + name); failures++; } }
    public static void main(String[] args) throws Exception {
        StringBuilder sb = new StringBuilder();
        String r = Task.transcribe(sb, false);
        check(r != null && r.equals("ab"), "committed: " + r);
        StringBuilder sb2 = new StringBuilder();
        String r2 = null;
        try { Task.transcribe(sb2, true); } catch (RuntimeException e) { r2 = "rethrown"; }
        check("rethrown".equals(r2), "exception propagated");
        check(sb2.length() == 0, "nothing flushed on rollback");
        boolean t = false;
        Task.Ledger l = new Task.Ledger(new StringBuilder());
        l.close();
        try { l.close(); } catch (IllegalStateException e) { t = true; }
        check(t, "double close");
        boolean t2 = false;
        try { l.add("x"); } catch (IllegalStateException e) { t2 = true; }
        check(t2, "add after close");
        if (failures > 0) { System.out.println(failures + " failures"); System.exit(1); }
        System.out.println("OK");
    }
}
