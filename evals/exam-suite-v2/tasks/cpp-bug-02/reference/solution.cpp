#include "solution.h"
#include <stdexcept>

Buffer::Buffer(std::size_t n) : data_(new unsigned char[n]()), n_(n) {}

Buffer::Buffer(const Buffer& other) : data_(new unsigned char[other.n_]), n_(other.n_) {
    for (std::size_t i = 0; i < n_; ++i) data_[i] = other.data_[i];
}

Buffer& Buffer::operator=(const Buffer& other) {
    if (this != &other) {
        unsigned char* fresh = new unsigned char[other.n_];
        for (std::size_t i = 0; i < other.n_; ++i) fresh[i] = other.data_[i];
        delete[] data_;
        data_ = fresh;
        n_ = other.n_;
    }
    return *this;
}

Buffer::~Buffer() { delete[] data_; }

unsigned char& Buffer::byte(std::size_t i) {
    if (i >= n_) throw std::out_of_range("byte");
    return data_[i];
}

std::size_t Buffer::size() const { return n_; }
