#ifndef JSONPARSER_PARSE_H
#define JSONPARSER_PARSE_H

/* Parse a non-negative integer from the start of `text`.
 * Returns the value, or -1 if the text does not begin with a digit. */
long parse_uint(const char *text);

#endif
