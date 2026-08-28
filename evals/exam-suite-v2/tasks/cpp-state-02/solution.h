#pragma once
#include <memory>
// Ведро токенов: старт - burst; tick() добавляет rate (не выше burst);
// allow(cost) при tokens >= cost списывает и true, иначе false; cost <= 0 - std::invalid_argument.
class TokenBucket {
public:
    TokenBucket(long rate, long burst);
    ~TokenBucket();
    TokenBucket(const TokenBucket&) = delete;
    TokenBucket& operator=(const TokenBucket&) = delete;
    void tick();
    bool allow(long cost = 1);
    long tokens() const;
private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};
