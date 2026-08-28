#pragma once
#include <string>
#include <vector>
// report(v): "sum=<S>;max=<M>;avg=<A>" (avg - целочисленное деление, пустой вектор: сумма 0,
// max 0, avg 0). Формат изменить нельзя.
std::string report(const std::vector<int>& v);
