import java.util.List;
public class TestMain {
    static int failures = 0;
    static void check(boolean c, String name) { if (!c) { System.out.println("FAIL " + name); failures++; } }
    public static void main(String[] args) {
        Task.LRUCache c = new Task.LRUCache(2);
        c.put("a", "1"); c.put("b", "2"); c.put("c", "3");
        check(c.get("a") == null && "2".equals(c.get("b")) && "3".equals(c.get("c")), "evict");
        Task.LRUCache d = new Task.LRUCache(2);
        d.put("a", "1"); d.put("b", "2"); d.get("a"); d.put("c", "3");
        check("1".equals(d.get("a")) && d.get("b") == null, "refresh");
        Task.LRUCache e = new Task.LRUCache(2);
        e.put("a", "1"); e.put("a", "9");
        check(e.size() == 1 && "9".equals(e.get("a")), "update");
        Task.LRUCache f = new Task.LRUCache(3);
        f.put("a", "1"); f.put("b", "2"); f.get("a");
        check(f.keys().equals(List.of("a", "b")), "keys order");
        final String[] evicted = new String[1];
        Task.LRUCache g = new Task.LRUCache(1, (k, v) -> evicted[0] = k + "=" + v);
        g.put("a", "1"); g.put("b", "2");
        check("a=1".equals(evicted[0]), "evict cb");
        if (failures > 0) { System.out.println(failures + " failures"); System.exit(1); }
        System.out.println("OK");
    }
}
