import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.function.BiConsumer;

public class Task {
    public static final class LRUCache {
        private final int capacity;
        private final LinkedHashMap<String, String> map;
        private final BiConsumer<String, String> onEvict;

        public LRUCache(int capacity) {
            this(capacity, null);
        }

        public LRUCache(int capacity, BiConsumer<String, String> onEvict) {
            this.capacity = capacity;
            this.onEvict = onEvict;
            this.map = new LinkedHashMap<>(16, 0.75f, true);
        }

        public String get(String key) {
            return map.getOrDefault(key, null);
        }

        public void put(String key, String value) {
            map.put(key, value);
            if (map.size() > capacity) {
                String oldest = map.keySet().iterator().next();
                String v = map.remove(oldest);
                if (onEvict != null) onEvict.accept(oldest, v);
            }
        }

        public int size() {
            return map.size();
        }

        public List<String> keys() {
            List<String> out = new ArrayList<>(map.keySet());
            java.util.Collections.reverse(out);
            return out;
        }
    }
}
