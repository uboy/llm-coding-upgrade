import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class Task {
    public static int[] minWindow(List<String> events, List<String> required) {
        if (required.isEmpty()) return new int[]{0, 0};
        Map<String, Integer> need = new HashMap<>();
        for (String t : required) need.merge(t, 1, Integer::sum);
        int missing = required.size();
        int[] best = null;
        int i = 0;
        for (int j = 0; j < events.size(); j++) {
            String tag = events.get(j);
            if (need.containsKey(tag)) {
                if (need.get(tag) > 0) missing--;
                need.merge(tag, -1, Integer::sum);
            }
            while (missing == 0) {
                if (best == null || j + 1 - i < best[1] - best[0]) best = new int[]{i, j + 1};
                String left = events.get(i);
                if (need.containsKey(left)) {
                    int nv = need.merge(left, 1, Integer::sum);
                    if (nv > 0) missing++;
                }
                i++;
            }
        }
        return best;
    }
}
