public class Task {
    public static final class Ledger implements AutoCloseable {
        private final java.lang.Appendable out;
        private final StringBuilder buffer = new StringBuilder();
        private boolean closed = false;
        private boolean committed = false;

        public Ledger(java.lang.Appendable out) {
            this.out = out;
        }

        public void add(String s) {
            if (closed) throw new IllegalStateException("closed");
            buffer.append(s);
        }

        @Override
        public void close() {
            if (closed) throw new IllegalStateException("already closed");
            closed = true;
        }

        /** Сброс накопленного в out одним вызовом append; только после close и один раз. */
        public void commit() {
            if (!closed || committed) throw new IllegalStateException("commit unavailable");
            committed = true;
            try {
                out.append(buffer);
            } catch (java.io.IOException e) {
                throw new RuntimeException(e);
            }
        }
    }

    public static String transcribe(Appendable out, boolean failMidway) {
        Ledger ledger = new Ledger(out);
        try (Ledger l = ledger) {
            l.add("a");
            l.add("b");
            if (failMidway) throw new RuntimeException("midway");
        }
        if (failMidway) return null;
        ledger.commit();
        return out.toString();
    }
}
