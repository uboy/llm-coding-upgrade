public class Task {
    public static int countOverlapping(String haystack, String needle) {
        if (needle.isEmpty()) return 0;
        int count = 0;
        int idx = haystack.indexOf(needle);
        while (idx >= 0) {
            count++;
            idx = haystack.indexOf(needle, idx + needle.length());
        }
        return count;
    }
}
