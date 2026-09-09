#include "parse.h"
#include <assert.h>

int main(void) {
    assert(parse_uint("123") == 123);
    assert(parse_uint("0") == 0);
    assert(parse_uint("x") == -1);
    return 0;
}
