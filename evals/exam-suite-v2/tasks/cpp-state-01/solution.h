#pragma once
#include <cstddef>
#include <memory>
#include <vector>
// Кольцевой буфер фиксированной ёмкости. Публичный контракт менять нельзя (pimpl).
class RingBuffer {
public:
    explicit RingBuffer(std::size_t capacity);
    ~RingBuffer();
    RingBuffer(const RingBuffer&) = delete;
    RingBuffer& operator=(const RingBuffer&) = delete;
    void push(int x);                    // переполнение перезаписывает старейший
    std::vector<int> snapshot() const;   // от старейшего к новейшему
    int last() const;                    // пусто - std::out_of_range
private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};
