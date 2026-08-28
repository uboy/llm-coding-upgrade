import java.util.ArrayList;
import java.util.List;
import java.util.Map;

public class Task {
    public static List<String> validateForm(Map<String, String> data) {
        List<String> errors = new ArrayList<>();
        if (!data.containsKey("name")) errors.add("no_name");
        if (!data.containsKey("age")) errors.add("no_age");
        else {
            int a = Integer.parseInt(data.get("age"));
            if (a < 18) errors.add("age_minor");
            else if (a > 150) errors.add("age_impossible");
        }
        if (!data.containsKey("email")) errors.add("no_email");
        else {
            String e = data.get("email");
            if (!e.contains("@") || e.startsWith("@") || e.endsWith("@")) errors.add("email_bad");
        }
        return errors;
    }
}
