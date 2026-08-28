public class TestMain {
    static int failures = 0;
    static void check(boolean c, String name) {
        if (!c) { System.out.println("FAIL " + name); failures++; }
    }
    public static void main(String[] args) {
        check(java.util.Arrays.equals(Task.firstFreeSlot(new int[][]{{60,120}}, 30, 0, 240), new int[]{0,30}), "gap");
        check(java.util.Arrays.equals(Task.firstFreeSlot(new int[][]{{0,60},{90,240}}, 30, 0, 240), new int[]{60,90}), "between");
        check(java.util.Arrays.equals(Task.firstFreeSlot(new int[][]{{0,100},{50,150}}, 50, 0, 240), new int[]{150,200}), "merge");
        check(Task.firstFreeSlot(new int[][]{{0,240}}, 10, 0, 240) == null, "no room");
        check(java.util.Arrays.equals(Task.firstFreeSlot(new int[][]{{30,30}}, 40, 0, 100), new int[]{0,40}), "zero len");
        boolean threw = false;
        try { Task.firstFreeSlot(new int[][]{}, 0, 0, 100); } catch (IllegalArgumentException e) { threw = true; }
        check(threw, "bad duration");
        if (failures > 0) { System.out.println(failures + " failures"); System.exit(1); }
        System.out.println("OK");
    }
}
