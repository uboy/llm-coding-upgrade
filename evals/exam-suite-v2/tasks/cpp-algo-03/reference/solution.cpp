#include "solution.h"
#include <algorithm>
#include <set>
#include <stdexcept>

std::vector<std::string> cooking_order(const std::map<std::string, std::vector<std::string>>& deps) {
    std::set<std::string> nodes;
    for (const auto& [k, v] : deps) {
        nodes.insert(k);
        for (const auto& d : v) nodes.insert(d);
    }
    std::map<std::string, int> indeg;
    std::map<std::string, std::vector<std::string>> adj;
    for (const auto& n : nodes) { indeg[n] = 0; adj[n] = {}; }
    for (const auto& [dish, needs] : deps)
        for (const auto& need : needs) { adj[need].push_back(dish); indeg[dish] += 1; }
    std::vector<std::string> heap;
    for (const auto& [n, d] : indeg) if (d == 0) heap.push_back(n);
    std::vector<std::string> order;
    while (!heap.empty()) {
        std::sort(heap.begin(), heap.end());
        std::string n = heap.front();
        heap.erase(heap.begin());
        order.push_back(n);
        for (const auto& m : adj[n]) if (--indeg[m] == 0) heap.push_back(m);
    }
    if (order.size() != nodes.size()) throw std::invalid_argument("cycle");
    return order;
}
