#pragma once
#include <cstdio>
#include <string>
// RAII-обёртка над файлом: только move (копирование запрещено с осмысленным сообщением).
// acquire(path, mode) в конструкторе; бросает std::runtime_error при неудаче fopen.
// Деструктор закрывает файл (если открыт). write(line) пишет строку + '\n'.
class FileGuard {
public:
    explicit FileGuard(const std::string& path, const std::string& mode);
    ~FileGuard();
    FileGuard(const FileGuard&) = delete;
    FileGuard& operator=(const FileGuard&) = delete;
    FileGuard(FileGuard&& other) noexcept;
    FileGuard& operator=(FileGuard&& other) noexcept;
    bool is_open() const;
    void write(const std::string& line);
private:
    std::FILE* file_ = nullptr;
};
