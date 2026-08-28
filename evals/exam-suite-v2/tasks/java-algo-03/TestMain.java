import java.util.List;
import java.util.Map;
public class TestMain {
    static int failures = 0;
    static void check(boolean c, String name) { if (!c) { System.out.println("FAIL " + name); failures++; } }
    public static void main(String[] args) {
        check(Task.cookingOrder(Map.of("b", List.of("a"), "a", List.of())).equals(List.of("a", "b")), "chain");
        check(Task.cookingOrder(Map.of("z", List.of(), "a", List.of(), "m", List.of("a"))).equals(List.of("a", "m", "z")), "lex");
        List<String> got = Task.cookingOrder(Map.of("d", List.of("b", "c"), "b", List.of("a"), "c", List.of("a"), "a", List.of()));
        check(got.size() == 4 && got.indexOf("a") < got.indexOf("b") && got.indexOf("a") < got.indexOf("c")
              && got.indexOf("b") < got.indexOf("d") && got.indexOf("c") < got.indexOf("d"), "diamond");
        boolean threw = false;
        try { Task.cookingOrder(Map.of("a", List.of("b"), "b", List.of("a"))); } catch (IllegalArgumentException e) { threw = true; }
        check(threw, "cycle");
        check(Task.cookingOrder(Map.of("a", List.of("x"))).equals(List.of("x", "a")), "leaf");
        if (failures > 0) { System.out.println(failures + " failures"); System.exit(1); }
        System.out.println("OK");
    }
}
