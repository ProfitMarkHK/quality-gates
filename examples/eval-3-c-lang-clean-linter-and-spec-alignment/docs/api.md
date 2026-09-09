# jsonparser — technical notes

`long parse_uint(const char *text)` — see include/parse.h. Pure function, no
allocation, no global state. Callers must pass a NUL-terminated string or NULL.
