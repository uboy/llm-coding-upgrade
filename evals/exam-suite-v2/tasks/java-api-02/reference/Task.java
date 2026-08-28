import java.util.ArrayList;
import java.util.List;

public class Task {
    public static List<String> validNumbers(List<String> numbers) {
        List<String> out = new ArrayList<>();
        for (String n : numbers) {
            int dash = n.indexOf('-');
            boolean ok = n.length() >= 5 && n.charAt(0) == 'G' && dash > 1 && dash == n.lastIndexOf('-')
                    && dash >= 3 && dash <= 7 && n.length() - dash - 1 >= 1 && n.length() - dash - 1 <= 4;
            if (ok) {
                for (int i = 1; i < dash; i++) if (!Character.isDigit(n.charAt(i))) ok = false;
                for (int i = dash + 1; i < n.length() && ok; i++) if (!Character.isDigit(n.charAt(i))) ok = false;
                if (ok && n.charAt(dash + 1) == '0') ok = false;
            }
            if (ok) out.add(n);
        }
        return out;
    }
}
