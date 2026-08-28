import java.time.LocalDate;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;

public class Task {
    @SuppressWarnings("unchecked")
    public static Map<String, Object> process(List<String> entries) {
        Map<String, Long> balances = new HashMap<>();
        List<String> skipped = new ArrayList<>();
        Pattern amount = Pattern.compile("[0-9]+");
        Pattern date = Pattern.compile("[0-9]{2}\\.[0-9]{2}\\.[0-9]{4}");
        for (String e : entries) {
            String[] parts = e.split("\\|", -1);
            boolean ok = parts.length == 4;
            if (ok) ok = amount.matcher(parts[3]).matches();
            if (ok) ok = date.matcher(parts[0]).matches();
            LocalDate d = null;
            if (ok) {
                try {
                    d = LocalDate.of(Integer.parseInt(parts[0].substring(6, 10)),
                                     Integer.parseInt(parts[0].substring(3, 5)),
                                     Integer.parseInt(parts[0].substring(0, 2)));
                } catch (Exception ex) { ok = false; }
            }
            if (ok) ok = parts[2].equals("D") || parts[2].equals("C");
            if (!ok) { skipped.add(e); continue; }
            long delta = parts[2].equals("C") ? Long.parseLong(parts[3]) : -Long.parseLong(parts[3]);
            balances.merge(parts[1], delta, Long::sum);
        }
        Map<String, Object> out = new HashMap<>();
        out.put("balances", balances);
        out.put("skipped", skipped);
        return out;
    }
}
