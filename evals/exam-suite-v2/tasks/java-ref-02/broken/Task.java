public class Task {
    public static long calc(String plan, long minutes) {
        switch (plan) {
            case "light": return minutes <= 30 ? 0 : (minutes - 30) * 150;
            case "standard": return minutes <= 100 ? 0 : (minutes - 100) * 100;
            case "premium": return minutes <= 300 ? 0 : (minutes - 300) * 80;
            default: throw new IllegalArgumentException("plan");
        }
    }
}
