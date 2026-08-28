import java.util.GregorianCalendar;

public class Task {
    private static final String[] MONTHS = {"январь","февраль","март","апрель","май","июнь","июль","август","сентябрь","октябрь","ноябрь","декабрь"};

    public static String monthName(String isoDate) {
        String[] p = isoDate.split("-");
        int y = Integer.parseInt(p[0]);
        int m = Integer.parseInt(p[1]);
        int d = Integer.parseInt(p[2]);
        GregorianCalendar c = new GregorianCalendar(y, m, d);
        return MONTHS[c.get(GregorianCalendar.MONTH)];
    }
}
