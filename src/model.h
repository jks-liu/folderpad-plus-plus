#pragma once
#include <windows.h>
#include <algorithm>
#include <string>
#include <vector>

namespace folderpad {
inline bool equal(const std::wstring& a, const std::wstring& b) {
    return CompareStringOrdinal(a.c_str(), static_cast<int>(a.size()), b.c_str(), static_cast<int>(b.size()), TRUE) == CSTR_EQUAL;
}
inline bool absolute(const std::wstring& p) {
    return (p.size() >= 3 && p[1] == L':' && (p[2] == L'\\' || p[2] == L'/')) ||
           (p.size() > 2 && p[0] == L'\\' && p[1] == L'\\');
}
// Lexical normalization only: never enumerate directories or resolve network links.
inline std::wstring normalize(std::wstring p) {
    std::replace(p.begin(), p.end(), L'/', L'\\');
    if (p.rfind(L"\\\\?\\UNC\\", 0) == 0) p = L"\\\\" + p.substr(8);
    else if (p.rfind(L"\\\\?\\", 0) == 0) p.erase(0, 4);
    if (!absolute(p)) return {};
    DWORD n = GetFullPathNameW(p.c_str(), 0, nullptr, nullptr);
    if (!n) return {};
    std::wstring full(n, L'\0');
    DWORD used = GetFullPathNameW(p.c_str(), n, full.data(), nullptr);
    if (!used || used >= n) return {};
    full.resize(used);
    while (full.size() > 3 && full.back() == L'\\') full.pop_back();
    return full;
}
inline int owner(const std::wstring& file, const std::vector<std::wstring>& folders) {
    auto path = normalize(file);
    int best = -1;
    size_t length = 0;
    for (size_t i = 0; i < folders.size(); ++i) {
        const auto& root = folders[i];
        if (root.empty() || path.size() <= root.size() || root.size() <= length) continue;
        if (equal(path.substr(0, root.size()), root) && (root.back() == L'\\' || path[root.size()] == L'\\')) {
            best = static_cast<int>(i);
            length = root.size();
        }
    }
    return best;
}
inline std::wstring leaf(const std::wstring& p) {
    auto pos = p.find_last_of(L"\\/");
    return pos == std::wstring::npos || pos + 1 == p.size() ? p : p.substr(pos + 1);
}
}
