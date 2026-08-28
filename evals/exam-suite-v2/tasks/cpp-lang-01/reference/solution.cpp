#include "solution.h"
#include <stdexcept>
#include <utility>

FileGuard::FileGuard(const std::string& path, const std::string& mode)
    : file_(std::fopen(path.c_str(), mode.c_str())) {
    if (!file_) throw std::runtime_error("cannot open " + path);
}

FileGuard::~FileGuard() {
    if (file_) std::fclose(file_);
}

FileGuard::FileGuard(FileGuard&& other) noexcept : file_(other.file_) {
    other.file_ = nullptr;
}

FileGuard& FileGuard::operator=(FileGuard&& other) noexcept {
    if (this != &other) {
        if (file_) std::fclose(file_);
        file_ = other.file_;
        other.file_ = nullptr;
    }
    return *this;
}

bool FileGuard::is_open() const { return file_ != nullptr; }

void FileGuard::write(const std::string& line) {
    if (!file_) throw std::runtime_error("closed");
    std::fputs(line.c_str(), file_);
    std::fputc('\n', file_);
}
