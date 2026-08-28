public class Task {
    public static long parseDuration(String s) {
        if (s.isEmpty()) throw new IllegalArgumentException("empty");
        String units = "dhms";
        long[] mul = {86400, 3600, 60, 1};
        int[] maxv = {0, 23, 59, 59};
        int prev = -1;
        long total = 0;
        int i = 0;
        while (i < s.length()) {
            if (!Character.isDigit(s.charAt(i))) throw new IllegalArgumentException("digit");
            long num = 0;
            boolean leading = s.charAt(i) == '0';
            while (i < s.length() && Character.isDigit(s.charAt(i))) { num = num * 10 + (s.charAt(i) - '0'); i++; }
            if (num == 0 || leading) throw new IllegalArgumentException("number");
            if (i >= s.length()) throw new IllegalArgumentException("unit");
            char u = s.charAt(i++);
            int ui = units.indexOf(u);
            if (ui < 0) throw new IllegalArgumentException("unit");
            if (prev != -1 && ui <= prev) throw new IllegalArgumentException("order");
            if (maxv[ui] != 0 && num > maxv[ui]) throw new IllegalArgumentException("range");
            total += num * mul[ui];
            prev = ui;
        }
        return total;
    }
}
