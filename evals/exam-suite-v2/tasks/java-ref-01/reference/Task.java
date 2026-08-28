import java.util.ArrayList;
import java.util.List;
import java.util.Map;

public class Task {
    private interface Rule {
        void apply(Map<String, String> data, List<String> errors);
    }

    private static final List<Rule> RULES = List.of(
        (d, e) -> { if (!d.containsKey("name")) e.add("no_name"); },
        (d, e) -> {
            if (!d.containsKey("age")) { e.add("no_age"); return; }
            int a = Integer.parseInt(d.get("age"));
            if (a < 18) e.add("age_minor");
            else if (a > 150) e.add("age_impossible");
        },
        (d, e) -> {
            if (!d.containsKey("email")) { e.add("no_email"); return; }
            String s = d.get("email");
            if (!s.contains("@") || s.startsWith("@") || s.endsWith("@")) e.add("email_bad");
        }
    );

    public static List<String> validateForm(Map<String, String> data) {
        List<String> errors = new ArrayList<>();
        for (Rule r : RULES) r.apply(data, errors);
        return errors;
    }
}
