#include "model.h"
#include <iostream>
#include <cstdlib>
int checks = 0;
void check(bool condition, const char* message) {
    ++checks;
    if (!condition) { std::cerr << "FAIL: " << message << '\n'; std::exit(1); }
}
int main() {
    using namespace folderpad;
    std::vector<std::wstring> roots{normalize(L"C:\\work"), normalize(L"C:\\work\\nested"), normalize(L"D:\\"), normalize(L"\\\\server\\share\\项目")};
    check(owner(L"C:\\work\\a.txt", roots) == 0, "direct child");
    check(owner(L"c:/WORK/nested/a.txt", roots) == 1, "longest and case insensitive");
    check(owner(L"C:\\work-other\\a.txt", roots) == -1, "directory boundary");
    check(owner(L"C:\\work", roots) == -1, "root itself is not a child");
    check(owner(L"new 1", roots) == -1, "unsaved document");
    check(owner(L"D:\\a.txt", roots) == 2, "drive root");
    check(owner(L"\\\\server\\share\\项目\\中文.txt", roots) == 3, "UNC unicode");
    check(owner(L"C:\\work\\nested\\..\\a.txt", roots) == 0, "dot segments");
    check(owner(L"\\\\?\\C:\\work\\nested\\a.txt", roots) == 1, "extended drive");
    check(owner(L"\\\\?\\UNC\\server\\share\\项目\\a.txt", roots) == 3, "extended UNC");
    check(normalize(L"C:/work///") == L"C:\\work", "trailing separators");
    check(normalize(L"relative").empty(), "reject relative roots");
    check(owner(L"C:\\work\\a.txt", {}) == -1, "no folders");
    roots.erase(roots.begin() + 1);
    check(owner(L"C:\\work\\nested\\a.txt", roots) == 0, "remove nested fallback");
    std::wstring longPath = L"C:\\work\\" + std::wstring(300, L'x') + L"\\a.txt";
    check(owner(longPath, roots) == 0, "long path");
    check(equal(L"C:\\Ä", L"c:\\ä"), "ordinal unicode case");
    std::cout << checks << " model checks passed\n";
}
