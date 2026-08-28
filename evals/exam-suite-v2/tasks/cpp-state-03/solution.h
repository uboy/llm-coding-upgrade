#pragma once
#include <cstddef>
#include <memory>
// Move-only буфер с подсчётом живых аллокаций (static live_buffers()).
class IntBuffer {
public:
    explicit IntBuffer(std::size_t n);     // n int, заполнены нулями
    ~IntBuffer();
    IntBuffer(const IntBuffer&) = delete;
    IntBuffer& operator=(const IntBuffer&) = delete;
    IntBuffer(IntBuffer&& other) noexcept;
    IntBuffer& operator=(IntBuffer&& other) noexcept;
    int& at(std::size_t i);                // вне диапазона - std::out_of_range; у перемещённого size()==0
    int at(std::size_t i) const;
    std::size_t size() const;
    static int live_buffers();
private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};
