#include "solution.h"

std::vector<int> remove_evens(std::vector<int> v) {
    for (std::size_t i = 0; i < v.size(); ++i) {
        if (v[i] % 2 == 0) {
            v.erase(v.begin() + i);
        }
    }
    return v;
}
