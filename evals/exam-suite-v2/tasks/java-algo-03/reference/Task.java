import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeSet;

public class Task {
    public static List<String> cookingOrder(Map<String, List<String>> deps) {
        TreeSet<String> nodes = new TreeSet<>();
        Map<String, List<String>> adj = new HashMap<>();
        Map<String, Integer> indeg = new HashMap<>();
        for (Map.Entry<String, List<String>> e : deps.entrySet()) {
            nodes.add(e.getKey());
            adj.putIfAbsent(e.getKey(), new ArrayList<>());
            indeg.putIfAbsent(e.getKey(), 0);
            for (String d : e.getValue()) {
                nodes.add(d);
                adj.putIfAbsent(d, new ArrayList<>());
                indeg.putIfAbsent(d, 0);
                adj.get(d).add(e.getKey());
                indeg.merge(e.getKey(), 1, Integer::sum);
            }
        }
        TreeSet<String> heap = new TreeSet<>();
        for (String n : nodes) if (indeg.get(n) == 0) heap.add(n);
        List<String> order = new ArrayList<>();
        while (!heap.isEmpty()) {
            String n = heap.pollFirst();
            order.add(n);
            for (String m : adj.get(n)) {
                int d = indeg.merge(m, -1, Integer::sum);
                if (d == 0) heap.add(m);
            }
        }
        if (order.size() != nodes.size()) throw new IllegalArgumentException("cycle");
        return order;
    }
}
