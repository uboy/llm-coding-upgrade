public class Task {
    public static boolean validInventory(String code) {
        if (code.length() != 10) return false;
        int sum = 0;
        for (int i = 0; i < 9; i++) {
            char c = code.charAt(i);
            if (!Character.isDigit(c)) return false;
            sum += (c - '0') * (10 - i);
        }
        int rem = sum % 11;
        char expected = rem == 10 ? 'X' : (char) ('0' + rem);
        char got = Character.toUpperCase(code.charAt(9));
        return got == expected && (Character.isDigit(code.charAt(9)) || code.charAt(9) == 'X' || code.charAt(9) == 'x');
    }
}
