#include "solution.h"
#include <sstream>
#include <type_traits>

template <typename T>
std::string render(const std::vector<T>& v) {
    static_assert(std::is_integral<T>::value || std::is_floating_point<T>::value ||
                      std::is_same<T, std::string>::value,
                  "unsupported type");
    std::ostringstream out;
    for (size_t i = 0; i < v.size(); ++i) {
        if (i) out << ", ";
        if constexpr (std::is_same<T, std::string>::value) {
            out << '"' << v[i] << '"';
        } else if constexpr (std::is_floating_point<T>::value) {
            out << std::to_string(v[i]);
        } else {
            out << v[i];
        }
    }
    return out.str();
}

template std::string render<int>(std::vector<int> const&);
template std::string render<long>(std::vector<long> const&);
template std::string render<double>(std::vector<double> const&);
template std::string render<std::string>(std::vector<std::string> const&);
