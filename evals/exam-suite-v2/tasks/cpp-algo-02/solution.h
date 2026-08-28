#pragma once
#include <string>
// "<count><symbol>[!]..." + "#N": развёрнутая строка; каждая '!' = +1 повтор предыдущего символа.
// Нет '#N' или сумма итоговых количеств (число + bang-повторы) mod 97 != N - std::invalid_argument.
std::string decode_beacon(const std::string& stream);
