#include "solution.h"

std::string report(const std::vector<int>& v) {
    int sum = 0;
    int max = 0;
    for (size_t i = 0; i < v.size(); ++i) {
        int x = v[i];
        sum = sum + x;
        if (x > max) {
            max = x;
        }
    }
    int avg = 0;
    if (v.size() > 0) {
        avg = sum / (int)v.size();
    }
    std::string out = "sum=";
    out = out + std::to_string(sum);
    out = out + ";max=";
    out = out + std::to_string(max);
    out = out + ";avg=";
    out = out + std::to_string(avg);
    return out;
}
