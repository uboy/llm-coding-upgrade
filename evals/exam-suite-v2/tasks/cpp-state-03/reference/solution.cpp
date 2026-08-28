#include "solution.h"
#include <stdexcept>
#include <utility>

namespace {
int g_live = 0;
}

struct IntBuffer::Impl {
    int* data = nullptr;
    std::size_t n = 0;
};

IntBuffer::IntBuffer(std::size_t n) : impl_(new Impl) {
    if (n > 0) {
        impl_->data = new int[n];
        for (std::size_t i = 0; i < n; ++i) impl_->data[i] = 0;
        ++g_live;
    }
    impl_->n = n;
}

IntBuffer::~IntBuffer() {
    if (impl_ && impl_->data) {
        delete[] impl_->data;
        --g_live;
    }
}

IntBuffer::IntBuffer(IntBuffer&& other) noexcept : impl_(std::move(other.impl_)) {}

IntBuffer& IntBuffer::operator=(IntBuffer&& other) noexcept {
    if (this != &other) {
        if (impl_ && impl_->data) { delete[] impl_->data; --g_live; }
        impl_ = std::move(other.impl_);
    }
    return *this;
}

int& IntBuffer::at(std::size_t i) {
    if (!impl_ || i >= impl_->n) throw std::out_of_range("at");
    return impl_->data[i];
}

int IntBuffer::at(std::size_t i) const {
    if (!impl_ || i >= impl_->n) throw std::out_of_range("at");
    return impl_->data[i];
}

std::size_t IntBuffer::size() const { return impl_ ? impl_->n : 0; }

int IntBuffer::live_buffers() { return g_live; }
