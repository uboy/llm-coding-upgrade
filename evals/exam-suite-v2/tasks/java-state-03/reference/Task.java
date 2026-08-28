import java.util.TreeSet;

public class Task {
    public static final class Elevator {
        private final int floors, capacity;
        private int current = 1;
        private int passengers = 0;
        private boolean doorsOpen = false;
        private final TreeSet<Integer> targets = new TreeSet<>();

        public Elevator(int floors, int capacity) {
            this.floors = floors;
            this.capacity = capacity;
        }

        public void call(int floor) {
            if (floor < 1 || floor > floors) throw new IllegalArgumentException("floor");
            targets.add(floor);
        }

        public void step() {
            if (doorsOpen) throw new IllegalStateException("doors open");
            if (targets.isEmpty()) return;
            int best = targets.first();
            for (int t : targets) {
                if (Math.abs(t - current) < Math.abs(best - current)
                        || (Math.abs(t - current) == Math.abs(best - current) && t < best)) best = t;
            }
            if (best > current) current++;
            else if (best < current) current--;
            if (current == best) {
                targets.remove(best);
                doorsOpen = true;
            }
        }

        public void board(int n) {
            if (!doorsOpen) throw new IllegalStateException("doors closed");
            if (passengers + n > capacity) throw new IllegalArgumentException("overload");
            passengers += n;
        }

        public int current() { return current; }
        public boolean doorsOpen() { return doorsOpen; }
        public int passengers() { return passengers; }
    }
}
