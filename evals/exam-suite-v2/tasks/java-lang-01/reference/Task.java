public class Task {
    public static final class Ledger implements AutoCloseable {
        private final Appendable out;
        private final StringBuilder buffer = new StringBuilder();
        private boolean closed = false;

        public Ledger(Appendable out) {
            this.out = out;
        }

        public void add(String s) {
            if (closed) throw new IllegalStateException("closed");
            buffer.append(s);
        }

        @Override
        public void close() throws IllegalStateException {
            if (closed) throw new IllegalStateException("already closed");
            closed = true;
        }

        public void flush() {
            if (!closed || buffer.length() == 0) return;
            try {
                out.append(buffer);
            } catch (java.io.IOException e) {
                throw new RuntimeException(e);
            }
            buffer.setLength(0);
        }
    }

    public static String transcribe(Appendable out, boolean failMidway) {
        Ledger ledger = new Ledger(out);
        try {
            ledger.add("a");
            ledger.add("b");
            if (failMidway) throw new RuntimeException("midway");
        } finally {
            try {
                ledger.close();
                if (!failMidway) ledger.flush();
            } catch (RuntimeException ignore) {
                // close может кинуть при повторе - здесь не ожидается
            }
        }
        if (failMidway) return null;
        return out.toString();
    }
}
