#pragma once
#include <cstddef>
// Буфер с ГЛУБОКОЙ копией: копия не разделяет память с оригиналом.
class Buffer {
public:
    explicit Buffer(std::size_t n);       // n байт, нули
    Buffer(const Buffer& other);          // глубокая копия
    Buffer& operator=(const Buffer& other);
    ~Buffer();
    unsigned char& byte(std::size_t i);   // вне диапазона - std::out_of_range
    std::size_t size() const;
private:
    unsigned char* data_;
    std::size_t n_;
};
