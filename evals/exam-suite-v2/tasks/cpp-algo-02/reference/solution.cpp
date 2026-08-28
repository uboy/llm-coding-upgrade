#include "solution.h"
#include <cctype>
#include <stdexcept>

std::string decode_beacon(const std::string& stream) {
    auto hash = stream.rfind('#');
    if (hash == std::string::npos) throw std::invalid_argument("no checksum");
    long cs = 0;
    for (size_t i = hash + 1; i < stream.size(); ++i) {
        if (!std::isdigit((unsigned char)stream[i])) throw std::invalid_argument("bad checksum");
        cs = cs * 10 + (stream[i] - '0');
    }
    std::string out;
    long total = 0;
    size_t i = 0;
    while (i < hash) {
        if (!std::isdigit((unsigned char)stream[i])) throw std::invalid_argument("bad fragment");
        long num = 0;
        while (i < hash && std::isdigit((unsigned char)stream[i])) { num = num * 10 + (stream[i] - '0'); ++i; }
        if (i >= hash) throw std::invalid_argument("missing symbol");
        char sym = stream[i++];
        long bangs = 0;
        while (i < hash && stream[i] == '!') { ++bangs; ++i; }
        long n = num + bangs;
        total += n;
        out.append(static_cast<size_t>(n), sym);
    }
    if (total % 97 != cs % 97) throw std::invalid_argument("checksum mismatch");
    return out;
}
