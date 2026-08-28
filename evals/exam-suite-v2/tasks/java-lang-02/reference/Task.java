import java.util.Comparator;
import java.util.List;

public class Task {
    public static <T extends Comparable<? super T>> T minOf(List<T> items) {
        return minOf(items, Comparator.naturalOrder());
    }

    public static <T> T minOf(List<T> items, Comparator<? super T> cmp) {
        if (items.isEmpty()) throw new IllegalArgumentException("empty");
        T best = items.get(0);
        for (T t : items) if (cmp.compare(t, best) < 0) best = t;
        return best;
    }
}
