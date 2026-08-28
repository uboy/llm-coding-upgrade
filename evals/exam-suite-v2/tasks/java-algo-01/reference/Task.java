import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

public class Task {
    public static int[] firstFreeSlot(int[][] busy, int duration, int dayStart, int dayEnd) {
        if (duration <= 0) throw new IllegalArgumentException("duration");
        List<int[]> iv = new ArrayList<>();
        for (int[] p : busy) if (p[1] > p[0]) iv.add(p);
        iv.sort((a, b) -> Integer.compare(a[0], b[0]));
        List<int[]> merged = new ArrayList<>();
        for (int[] p : iv) {
            if (!merged.isEmpty() && p[0] <= merged.get(merged.size() - 1)[1]) {
                int[] last = merged.get(merged.size() - 1);
                last[1] = Math.max(last[1], p[1]);
            } else merged.add(p);
        }
        int t = dayStart;
        for (int[] m : merged) {
            if (m[0] - t >= duration) return new int[]{t, t + duration};
            t = Math.max(t, m[1]);
        }
        if (dayEnd - t >= duration) return new int[]{t, t + duration};
        return null;
    }
}
