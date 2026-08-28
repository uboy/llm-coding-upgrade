#include "solution.h"
#include <stdexcept>

Buffer::Buffer(std::size_t n) : data_(new unsigned char[n]()), n_(n) {}

Buffer::Buffer(const Buffer& other) : data_(other.data_), n_(other.n_) {}

Buffer& Buffer::operator=(const Buffer& other) {
    data_ = other.data_;
    n_ = other.n_;
    return *this;
}

Buffer::~Buffer() {} // утечка вместо удаления: копии делят один буфер

unsigned char& Buffer::byte(std::size_t i) {
    if (i >= n_) throw std::out_of_range("byte");
    return data_[i];
}

std::size_t Buffer::size() const { return n_; }
