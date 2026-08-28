public class TestMain {
    static int failures = 0;
    static void check(boolean c, String name) { if (!c) { System.out.println("FAIL " + name); failures++; } }
    public static void main(String[] args) {
        check(Task.validInventory("0452317605"), "valid 5");
        check(Task.validInventory("0435172605") == false, "wrong ctrl");
        check(Task.validInventory("0452317605X") == false, "len 11");
        check(Task.validInventory("045231760") == false, "len 9");
        check(Task.validInventory("111111111X"), "X case");
        check(Task.validInventory("111111111x"), "x lower");
        check(Task.validInventory("1111111110") == false, "not X");
        check(Task.validInventory("A452317605") == false, "letter");
        if (failures > 0) { System.out.println(failures + " failures"); System.exit(1); }
        System.out.println("OK");
    }
}
