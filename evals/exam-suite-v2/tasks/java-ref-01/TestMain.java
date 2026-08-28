import java.util.List;
import java.util.Map;
public class TestMain {
    static int failures = 0;
    static void check(boolean c, String name) { if (!c) { System.out.println("FAIL " + name); failures++; } }
    public static void main(String[] args) {
        check(Task.validateForm(Map.of("name","Ann","age","30","email","a@b.co")).isEmpty(), "ok");
        check(Task.validateForm(Map.of()).equals(List.of("no_name","no_age","no_email")), "missing");
        check(Task.validateForm(Map.of("name","A","age","17","email","a@b.co")).equals(List.of("age_minor")), "minor");
        check(Task.validateForm(Map.of("name","A","age","151","email","a@b.co")).equals(List.of("age_impossible")), "impossible");
        check(Task.validateForm(Map.of("name","A","age","30","email","bob")).equals(List.of("email_bad")), "email");
        check(Task.validateForm(Map.of("age","10","email","x")).equals(List.of("no_name","age_minor","email_bad")), "multi");
        if (failures > 0) { System.out.println(failures + " failures"); System.exit(1); }
        System.out.println("OK");
    }
}
