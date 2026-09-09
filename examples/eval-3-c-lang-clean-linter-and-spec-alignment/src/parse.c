#include "parse.h"
#include <ctype.h>

long parse_uint(const char *text) {
    if (text == 0 || !isdigit((unsigned char)text[0])) {
        return -1;
    }
    long value = 0;
    for (const char *p = text; *p && isdigit((unsigned char)*p); ++p) {
        value = value * 10 + (*p - '0');
    }
    return value;
}
