import java.util.List;

public class Task {
    public static boolean sameOrder(Integer a, Integer b) {
        return a != null && a.equals(b);
    }

    public static int countMatches(List<Integer> orders, Integer probe) {
        int count = 0;
        for (Integer o : orders) if (sameOrder(o, probe)) count++;
        return count;
    }
}
