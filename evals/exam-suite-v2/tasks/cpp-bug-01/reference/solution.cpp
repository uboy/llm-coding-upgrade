#include "solution.h"

std::vector<int> remove_evens(std::vector<int> v) {
    std::vector<int> out;
    for (int x : v) if (x % 2 != 0) out.push_back(x);
    return out;
}
