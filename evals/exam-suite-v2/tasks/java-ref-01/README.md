# Рефактор: валидация анкеты "Анкета-3" (Java)

Task.java: `public static java.util.List<String> validateForm(java.util.Map<String, String> data)` — коды ошибок в порядке: no_name, no_age, age_minor, age_impossible, no_email, email_bad (age-коды взаимоисключающие: отсутствует возраст = только no_age; email-проверка: нет '@', начинается/заканчивается на '@').

Работает, но лесенкой. Отрефактори на список/цепочку проверок (List<Predicate>+Function или отдельные методы), сохранив порядок кодов и публичный API.
