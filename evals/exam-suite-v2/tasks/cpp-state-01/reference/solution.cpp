#include "solution.h"
#include <stdexcept>

struct RingBuffer::Impl {
    std::size_t cap;
    std::vector<int> buf;
    std::size_t head = 0;
    std::size_t size = 0;
};

RingBuffer::RingBuffer(std::size_t capacity) : impl_(new Impl{capacity, std::vector<int>(capacity, 0)}) {}
RingBuffer::~RingBuffer() = default;

void RingBuffer::push(int x) {
    if (impl_->cap == 0) throw std::invalid_argument("capacity 0");
    impl_->buf[impl_->head] = x;
    impl_->head = (impl_->head + 1) % impl_->cap;
    impl_->size = impl_->size < impl_->cap ? impl_->size + 1 : impl_->cap;
}

std::vector<int> RingBuffer::snapshot() const {
    std::vector<int> out;
    out.reserve(impl_->size);
    std::size_t start = (impl_->head + impl_->cap - impl_->size) % impl_->cap;
    for (std::size_t k = 0; k < impl_->size; ++k) out.push_back(impl_->buf[(start + k) % impl_->cap]);
    return out;
}

int RingBuffer::last() const {
    if (impl_->size == 0) throw std::out_of_range("empty");
    return impl_->buf[(impl_->head + impl_->cap - 1) % impl_->cap];
}
