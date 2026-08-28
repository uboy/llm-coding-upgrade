public class Task {
    public static String decodeBeacon(String stream) {
        int hash = stream.lastIndexOf('#');
        if (hash < 0) throw new IllegalArgumentException("no checksum");
        String csStr = stream.substring(hash + 1);
        for (char c : csStr.toCharArray()) if (!Character.isDigit(c)) throw new IllegalArgumentException("bad checksum");
        long cs = Long.parseLong(csStr);
        StringBuilder out = new StringBuilder();
        long total = 0;
        int i = 0;
        while (i < hash) {
            if (!Character.isDigit(stream.charAt(i))) throw new IllegalArgumentException("bad fragment");
            long num = 0;
            while (i < hash && Character.isDigit(stream.charAt(i))) { num = num * 10 + (stream.charAt(i) - '0'); i++; }
            if (i >= hash) throw new IllegalArgumentException("missing symbol");
            char sym = stream.charAt(i++);
            long bangs = 0;
            while (i < hash && stream.charAt(i) == '!') { bangs++; i++; }
            long n = num + bangs;
            total += n;
            for (long k = 0; k < n; k++) out.append(sym);
        }
        if (total % 97 != cs % 97) throw new IllegalArgumentException("checksum mismatch");
        return out.toString();
    }
}
