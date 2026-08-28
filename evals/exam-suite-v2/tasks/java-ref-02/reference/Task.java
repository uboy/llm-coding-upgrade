import java.util.Map;

public class Task {
    private static final Map<String, long[]> PLANS = Map.of(
        "light", new long[]{30, 150},
        "standard", new long[]{100, 100},
        "premium", new long[]{300, 80}
    );

    public static long calc(String plan, long minutes) {
        long[] p = PLANS.get(plan);
        if (p == null) throw new IllegalArgumentException("plan");
        long over = Math.max(0, minutes - p[0]);
        return over * p[1];
    }
}
