#include "solution.h"
#include <stdexcept>
#include <algorithm>

struct TokenBucket::Impl {
    long rate;
    long burst;
    long tokens_;
};

TokenBucket::TokenBucket(long rate, long burst) : impl_(new Impl{rate, burst, burst}) {}
TokenBucket::~TokenBucket() = default;

void TokenBucket::tick() { impl_->tokens_ = std::min(impl_->burst, impl_->tokens_ + impl_->rate); }

bool TokenBucket::allow(long cost) {
    if (cost <= 0) throw std::invalid_argument("cost");
    if (impl_->tokens_ >= cost) { impl_->tokens_ -= cost; return true; }
    return false;
}

long TokenBucket::tokens() const { return impl_->tokens_; }
