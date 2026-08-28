import java.time.LocalDate;
import java.time.format.DateTimeParseException;

public class Task {
    private static final String[] MONTHS = {"январь","февраль","март","апрель","май","июнь","июль","август","сентябрь","октябрь","ноябрь","декабрь"};

    public static String monthName(String isoDate) {
        try {
            LocalDate d = LocalDate.parse(isoDate);
            return MONTHS[d.getMonthValue() - 1];
        } catch (DateTimeParseException e) {
            throw new IllegalArgumentException("bad date");
        }
    }
}
