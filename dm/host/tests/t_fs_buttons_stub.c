// Test double for the Mac front end's pad family read (pad_family_mac.h): a strong definition of the weak hook hle_fs.c declares, returning the family the case set
extern const char *g_test_family;
const char *dm_pad_family(void) { return g_test_family; }
