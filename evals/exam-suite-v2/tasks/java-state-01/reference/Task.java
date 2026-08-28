public class Task {
    public static final class TokenBucket {
        private final long rate;
        private final long burst;
        private long tokens;

        public TokenBucket(long rate, long burst) {
            this.rate = rate;
            this.burst = burst;
            this.tokens = burst;
        }

        public void tick() {
            tokens = Math.min(burst, tokens + rate);
        }

        public boolean allow(long cost) {
            if (cost <= 0) throw new IllegalArgumentException("cost");
            if (tokens >= cost) {
                tokens -= cost;
                return true;
            }
            return false;
        }

        public long tokens() {
            return tokens;
        }
    }
}
