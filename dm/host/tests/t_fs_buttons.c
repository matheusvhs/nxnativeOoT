// RomFS button-mod overlay unit test (hle_fs.c's rom_overlay_env): DM_BUTTON_MODS' folder of one RomFS overlay per controller family, picked once per
// start by the connected gamepad's family (dm_pad_family, stubbed) or forced by DM_BUTTONS / DM_BOTOES, after the manual DM_ROMFS_OVERLAY folders.
// The choice is cached on the first rom mount, so every case runs in a forked child with a pristine cache. Expectations are hand-written.
#include <sys/types.h>
#include <sys/wait.h>
#include "../hle_fs.c"
struct dm_flags g_flag; uint64_t g_t0_ns;
uint64_t now_ns(void) { return 0; }
void dm_guest_write_prepare(void *a, size_t n) { (void)a; (void)n; }
module_t *g_mod; int g_nmod;   // Module table (MountSave picks save fixes by main build ID): this unit test loads no modules
static int checks, fails;
#define CHECK(c, ...) do { checks++; int ok = !!(c); fails += !ok; printf("%s ", ok ? "✓" : "✗"); printf(__VA_ARGS__); printf("\n"); } while (0)
const char *g_test_family;   // the family dm_pad_family (t_fs_buttons_stub.c's strong definition of hle_fs.c's weak hook, pad_family_mac.h's on the Mac) reports
static int content(const char *path, const char *want) {
    uint64_t h; if (h_fs_OpenFile(&h, path, MODE_READ)) return 0;
    char b[64] = {0}; size_t n = 0; Result r = h_fs_ReadFile(&n, h, 0, b, sizeof b);
    h_fs_CloseFile(h); return !r && n == strlen(want) && !memcmp(b, want, n);
}
static int absent(const char *path) { uint64_t h; Result r = h_fs_OpenFile(&h, path, MODE_READ); if (!r) h_fs_CloseFile(h); return r == RES_PATH_NOT_FOUND; }
static void put(const char *p, const char *s) { FILE *f = fopen(p, "w"); fputs(s, f); fclose(f); }

static const char *t_rom, *t_overlay, *t_mods, *t_buttons, *t_botoes, *t_family, *t_family_content;
static void set_env(void) {   // a child's environment, as the launcher and the player set it
    setenv("DM_ROMFS", t_rom, 1);
    if (t_overlay) setenv("DM_ROMFS_OVERLAY", t_overlay, 1); else unsetenv("DM_ROMFS_OVERLAY");
    if (t_mods) setenv("DM_BUTTON_MODS", t_mods, 1); else unsetenv("DM_BUTTON_MODS");
    if (t_buttons) setenv("DM_BUTTONS", t_buttons, 1); else unsetenv("DM_BUTTONS");
    if (t_botoes) setenv("DM_BOTOES", t_botoes, 1); else unsetenv("DM_BOTOES");
    g_test_family = t_family;
}
// The usual case: mount rom and check one file's content (NULL: the file must be absent, as of a family whose overlay is not taken)
static int mount_case(void) {
    set_env();
    if (h_fs_MountRom("rom", NULL, 0) != RES_OK) return 10;
    return t_family_content ? !content("rom:/data/same", t_family_content) : !absent("rom:/data/same");
}
// The manual overlay's roots precede the mod's: conflicting files read the manual content, and the mod's own files still read
static int mount_case_manual(void) {
    set_env();
    if (h_fs_MountRom("rom", NULL, 0) != RES_OK) return 10;
    if (!content("rom:/data/same", "manual") || !content("rom:/data/m", "mfile")) return 11;
    return !content("rom:/data/x", "xfile");
}
// Once per start: DM_BUTTONS changed after the first mount does not switch the overlay
static int mount_case_once(void) {
    set_env();
    if (h_fs_MountRom("rom", NULL, 0) != RES_OK || !content("rom:/data/same", "xmod")) return 10;
    g_nmnt = 0; setenv("DM_BUTTONS", "ps", 1);
    if (h_fs_MountRom("rom", NULL, 0) != RES_OK) return 11;
    return !content("rom:/data/same", "xmod");   // still xbox, not ps
}
static int in_child(int (*fn)(void)) { fflush(NULL); pid_t pid = fork(); if (!pid) _exit(fn()); int st = 0; waitpid(pid, &st, 0); return WIFEXITED(st) ? WEXITSTATUS(st) : 90; }

int main(void) {
    char root[1024];
    const char *tmp = getenv("TMPDIR");
    snprintf(root, sizeof root, "%s/buttons.XXXXXX", tmp ? tmp : "/private/tmp");
    if (!mkdtemp(root)) { perror("mkdtemp"); return 2; }
    char rom[1100], mods[1100], man[1200], empty[1100], p[1300];
    // rom: the game's own files; mods: one overlay folder per family, as button_mods/make_mods.py makes; man: a manual DM_ROMFS_OVERLAY folder
    snprintf(rom, sizeof rom, "%s/rom/data", root); snprintf(p, sizeof p, "%s/rom", root); mkdir(p, 0755); mkdir(rom, 0755);
    snprintf(p, sizeof p, "%s/same", rom); put(p, "base"); snprintf(p, sizeof p, "%s/base", rom); put(p, "only-base");
    snprintf(mods, sizeof mods, "%s/mods", root); mkdir(mods, 0755);
    snprintf(p, sizeof p, "%s/xbox", mods); mkdir(p, 0755); snprintf(p, sizeof p, "%s/xbox/data", mods); mkdir(p, 0755);
    snprintf(p, sizeof p, "%s/xbox/data/same", mods); put(p, "xmod"); snprintf(p, sizeof p, "%s/xbox/data/x", mods); put(p, "xfile");
    snprintf(p, sizeof p, "%s/ps", mods); mkdir(p, 0755); snprintf(p, sizeof p, "%s/ps/data", mods); mkdir(p, 0755);
    snprintf(p, sizeof p, "%s/ps/data/same", mods); put(p, "pmod");
    snprintf(man, sizeof man, "%s/man", root); snprintf(p, sizeof p, "%s/data", man); mkdir(man, 0755); mkdir(p, 0755);
    snprintf(p, sizeof p, "%s/data/same", man); put(p, "manual"); snprintf(p, sizeof p, "%s/data/m", man); put(p, "mfile");
    snprintf(empty, sizeof empty, "%s/empty", root); mkdir(empty, 0755);   // a DM_BUTTON_MODS folder holding no family's overlay
    char romroot[1100]; snprintf(romroot, sizeof romroot, "%s/rom", root); t_rom = romroot;
    const struct { const char *name, *mods, *buttons, *botoes, *family, *expect; } C[] = {
        {"DM_BUTTONS=xbox picks the Xbox overlay", mods, "xbox", NULL, NULL, "xmod"},
        {"DM_BUTTONS=ps picks the PlayStation overlay", mods, "ps", NULL, NULL, "pmod"},
        {"DM_BUTTONS wins over DM_BOTOES", mods, "xbox", "ps", NULL, "xmod"},
        {"DM_BOTOES is read when DM_BUTTONS is unset", mods, NULL, "ps", NULL, "pmod"},
        {"DM_BUTTONS=nintendo keeps the game's own buttons", mods, "nintendo", NULL, NULL, "base"},
        {"an Xbox pad connected at start", mods, NULL, NULL, "xbox", "xmod"},
        {"a PlayStation pad connected at start", mods, NULL, NULL, "ps", "pmod"},
        {"a Nintendo pad connected at start keeps the game's own buttons", mods, NULL, NULL, "nintendo", "base"},
        {"no pad connected keeps the game's own buttons", mods, NULL, NULL, NULL, "base"},
        {"DM_BUTTONS=auto detects the connected pad", mods, "auto", NULL, "ps", "pmod"},
        {"a family with no overlay folder keeps the game's own buttons", empty, NULL, NULL, "xbox", "base"},
        {"a forced name that is no family is no path either (../ps)", mods, "../mods/ps", NULL, NULL, "base"},
        {"a forced name that is no family is no path either (plain)", mods, "playstation", NULL, NULL, "base"},
        {"a detected name that is no family is no path either", mods, NULL, NULL, "../mods/ps", "base"},
        {"no DM_BUTTON_MODS keeps the game's own buttons", NULL, "xbox", NULL, NULL, "base"},
    };
    for (size_t i = 0; i < sizeof C / sizeof C[0]; i++) {
        t_mods = C[i].mods; t_buttons = C[i].buttons; t_botoes = C[i].botoes; t_family = C[i].family; t_overlay = NULL; t_family_content = C[i].expect;
        CHECK(in_child(mount_case) == 0, "%s", C[i].name);
    }
    t_overlay = man; t_mods = mods; t_buttons = "xbox"; t_botoes = NULL; t_family = NULL;
    CHECK(in_child(mount_case_manual) == 0, "a manual DM_ROMFS_OVERLAY wins over the mod, which still adds the files the manual folder lacks");
    t_overlay = man; t_mods = mods; t_buttons = "../mods/ps"; t_botoes = NULL; t_family = NULL; t_family_content = "manual";
    CHECK(in_child(mount_case) == 0, "an invalid forced name keeps the manual overlay alone");
    t_overlay = NULL; t_mods = mods; t_buttons = "xbox"; t_botoes = NULL; t_family = NULL;
    CHECK(in_child(mount_case_once) == 0, "the choice is made once per start");
    printf("== buttons: %d checks, %d failed ==\n", checks, fails); return fails != 0;
}
// the guest address space (hle_svc.c): the unit test has none, so every stack is a host stack (hle_bigstack.c)
int dm_guest_as_contains(uintptr_t a) { (void)a; return 0; }
// main's imports (loader.c) and the MiiModel stand-in (hle_mii.c): no main module, no system data
void *guest_sym(const char *name) { (void)name; return NULL; }
int dm_game_imports(const char *prefix) { (void)prefix; return 0; }
int dm_mii_standin(const char *dir) { (void)dir; return 0; }
void dm_thread_service_request(void) {}
