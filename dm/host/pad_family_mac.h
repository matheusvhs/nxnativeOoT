// Mac: the family of the gamepad connected when the game starts, for button mods (hle_fs.c, DM_BUTTON_MODS): "ps" for Sony (DualSense, DualShock 4), "xbox" for Microsoft,
// "nintendo" for Nintendo, NULL with no gamepad. The game mounts its RomFS before the run loop has turned, when GameController lists no controller yet, so the HID devices are read
// at once through IOKit (the vendor ID of every Generic Desktop gamepad or joystick), with GameController's list as a fallback (an Xbox pad on USB is not a HID device).
#pragma once
#import <IOKit/hid/IOHIDManager.h>
#import <GameController/GameController.h>

static const char *pad_family_of_vendor(int vid) { return vid == 0x054C ? "ps" : vid == 0x045E ? "xbox" : vid == 0x057E ? "nintendo" : NULL; }

const char *dm_pad_family(void) {
    const char *fam = NULL;
    IOHIDManagerRef m = IOHIDManagerCreate(kCFAllocatorDefault, kIOHIDOptionsTypeNone);
    if (m) {
        NSArray *match = @[@{@kIOHIDDeviceUsagePageKey: @(kHIDPage_GenericDesktop), @kIOHIDDeviceUsageKey: @(kHIDUsage_GD_GamePad)},
                           @{@kIOHIDDeviceUsagePageKey: @(kHIDPage_GenericDesktop), @kIOHIDDeviceUsageKey: @(kHIDUsage_GD_Joystick)}];
        IOHIDManagerSetDeviceMatchingMultiple(m, (__bridge CFArrayRef)match);
        if (IOHIDManagerOpen(m, kIOHIDOptionsTypeNone) == kIOReturnSuccess) {
            NSSet *devs = CFBridgingRelease(IOHIDManagerCopyDevices(m));
            for (id o in devs) {
                NSNumber *v = (__bridge NSNumber *)IOHIDDeviceGetProperty((__bridge IOHIDDeviceRef)o, CFSTR(kIOHIDVendorIDKey));
                if ((fam = pad_family_of_vendor(v.intValue))) break;
            }
            IOHIDManagerClose(m, kIOHIDOptionsTypeNone);
        }
        CFRelease(m);
    }
    if (!fam) for (GCController *c in GCController.controllers) {
        NSString *k = c.productCategory;
        if ([k containsString:@"DualSense"] || [k containsString:@"DualShock"]) { fam = "ps"; break; }
        if ([k containsString:@"Xbox"]) { fam = "xbox"; break; }
        if (dm_pad_labelled(c)) { fam = "nintendo"; break; }
    }
    return fam;
}
