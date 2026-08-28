#pragma once
#include <string>
#include <vector>
// render(v): элементы через ", ".
// - целые: как есть (std::to_string);
// - floating: как std::to_string (точка, хвостовые нули допустимы);
// - std::string: каждый элемент в двойных кавычках;
// - любой другой тип: ошибка КОМПИЛЯЦИИ (static_assert с сообщением "unsupported type").
// Реализуй шаблон в solution.cpp (if constexpr / <type_traits>), solution.h не менять.
template <typename T>
std::string render(const std::vector<T>& v);
