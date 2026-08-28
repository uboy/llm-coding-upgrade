#include "solution.h"
#include <algorithm>
#include <sstream>

namespace {

std::vector<std::string> split_logical_lines(const std::string& text) {
    std::vector<std::string> lines;
    std::string cur;
    bool in_q = false;
    for (size_t i = 0; i < text.size(); ++i) {
        char ch = text[i];
        if (ch == '"') { in_q = !in_q; cur += ch; continue; }
        if ((ch == '\n' || ch == '\r') && !in_q) {
            if (ch == '\r' && i + 1 < text.size() && text[i + 1] == '\n') ++i;
            lines.push_back(cur);
            cur.clear();
            continue;
        }
        cur += ch;
    }
    lines.push_back(cur);
    return lines;
}

std::vector<std::string> split_fields(const std::string& line, char delim) {
    std::vector<std::string> fields;
    std::string cur;
    bool in_q = false;
    for (size_t i = 0; i < line.size(); ++i) {
        char ch = line[i];
        if (ch == '"') {
            if (in_q && i + 1 < line.size() && line[i + 1] == '"') { cur += '"'; ++i; continue; }
            in_q = !in_q;
            continue;
        }
        if (ch == delim && !in_q) { fields.push_back(cur); cur.clear(); continue; }
        cur += ch;
    }
    fields.push_back(cur);
    return fields;
}

bool blank(const std::string& s) {
    for (char c : s) if (c != ' ' && c != '\t' && c != '\r') return false;
    return true;
}

} // namespace

std::vector<std::map<std::string, std::string>> parse_talka(const std::string& text) {
    std::vector<std::map<std::string, std::string>> rows;
    auto raw = split_logical_lines(text);
    std::vector<std::string> lines;
    for (auto& l : raw) if (!blank(l)) lines.push_back(l);
    if (lines.empty()) return rows;
    size_t commas = std::count(lines[0].begin(), lines[0].end(), ',');
    size_t semis = std::count(lines[0].begin(), lines[0].end(), ';');
    char delim = semis > commas ? ';' : ',';
    auto header = split_fields(lines[0], delim);
    for (size_t k = 1; k < lines.size(); ++k) {
        auto fields = split_fields(lines[k], delim);
        std::map<std::string, std::string> row;
        for (size_t c = 0; c < header.size(); ++c)
            row[header[c]] = c < fields.size() ? fields[c] : std::string();
        rows.push_back(std::move(row));
    }
    return rows;
}
