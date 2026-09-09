# jsonparser — functional specification

## FR-1 parse_uint
- Given a string that begins with one or more ASCII digits, `parse_uint`
  returns the decimal value of the leading digit run.
- Given a string that does not begin with a digit, it returns -1.
- Given a NULL pointer, it returns -1.

## FR-2 (planned, not yet implemented)
- `parse_uint` shall reject values that overflow `long` and return -2.
