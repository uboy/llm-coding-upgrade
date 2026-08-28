public class TestMain {
    static int failures = 0;
    static void check(boolean c, String name) { if (!c) { System.out.println("FAIL " + name); failures++; } }
    static void throwsIAE(String s, String name) {
        try { Task.parseDuration(s); check(false, name); }
        catch (IllegalArgumentException e) { check(true, name); }
    }
    public static void main(String[] args) {
        check(Task.parseDuration("1d") == 86400L, "1d");
        check(Task.parseDuration("2h30m") == 9000L, "2h30m");
        check(Task.parseDuration("1d2h3m4s") == 93784L, "full");
        throwsIAE("", "empty");
        throwsIAE("1d1d", "repeat");
        throwsIAE("3h2d", "order");
        throwsIAE("24h", "h range");
        throwsIAE("60m", "m range");
        throwsIAE("0s", "zero");
        throwsIAE("01s", "leading zero");
        throwsIAE("1 s", "space");
        if (failures > 0) { System.out.println(failures + " failures"); System.exit(1); }
        System.out.println("OK");
    }
}
