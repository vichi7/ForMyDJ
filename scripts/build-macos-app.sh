#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$ROOT/dist/ForMyDJ.app"
CONTENTS="$APP/Contents"
MACOS="$CONTENTS/MacOS"
RESOURCES="$CONTENTS/Resources"
LAUNCHER_C="$ROOT/dist/launcher.c"
LAUNCHER_M="$ROOT/dist/launcher.m"

rm -rf "$APP"
mkdir -p "$MACOS" "$RESOURCES"
cp -R "$ROOT/app" "$RESOURCES/app"

cat > "$CONTENTS/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key>
  <string>ForMyDJ</string>
  <key>CFBundleDisplayName</key>
  <string>ForMyDJ</string>
  <key>CFBundleIdentifier</key>
  <string>com.slavaporollo.formydj</string>
  <key>CFBundleVersion</key>
  <string>0.1.0</string>
  <key>CFBundleShortVersionString</key>
  <string>0.1.0</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleExecutable</key>
  <string>ForMyDJ</string>
  <key>LSMinimumSystemVersion</key>
  <string>12.0</string>
  <key>NSHighResolutionCapable</key>
  <true/>
  <key>NSAppTransportSecurity</key>
  <dict>
    <key>NSAllowsLocalNetworking</key>
    <true/>
  </dict>
</dict>
</plist>
PLIST

cat > "$LAUNCHER_M" <<'M'
#import <Cocoa/Cocoa.h>
#import <WebKit/WebKit.h>

@interface AppDelegate : NSObject <NSApplicationDelegate, WKNavigationDelegate>
@property(nonatomic, strong) NSWindow *window;
@property(nonatomic, strong) WKWebView *webView;
@property(nonatomic, strong) NSTask *serverTask;
@property(nonatomic) NSInteger loadAttempts;
@end

@implementation AppDelegate

- (void)applicationDidFinishLaunching:(NSNotification *)notification {
    [self buildMenu];
    [self startServer];
    [self buildWindow];
    [self loadAppAfterDelay];
}

- (BOOL)applicationShouldTerminateAfterLastWindowClosed:(NSApplication *)sender {
    return YES;
}

- (void)buildMenu {
    NSMenu *mainMenu = [[NSMenu alloc] initWithTitle:@""];
    NSMenuItem *appMenuItem = [[NSMenuItem alloc] initWithTitle:@""
                                                         action:nil
                                                  keyEquivalent:@""];
    NSMenuItem *editMenuItem = [[NSMenuItem alloc] initWithTitle:@""
                                                          action:nil
                                                   keyEquivalent:@""];
    [mainMenu addItem:appMenuItem];
    [mainMenu addItem:editMenuItem];

    NSMenu *appMenu = [[NSMenu alloc] initWithTitle:@"ForMyDJ"];
    [appMenu addItemWithTitle:@"Quit ForMyDJ"
                       action:@selector(terminate:)
                keyEquivalent:@"q"];
    appMenuItem.submenu = appMenu;

    NSMenu *editMenu = [[NSMenu alloc] initWithTitle:@"Edit"];
    [editMenu addItemWithTitle:@"Cut"
                        action:@selector(cut:)
                 keyEquivalent:@"x"];
    [editMenu addItemWithTitle:@"Copy"
                        action:@selector(copy:)
                 keyEquivalent:@"c"];
    [editMenu addItemWithTitle:@"Paste"
                        action:@selector(paste:)
                 keyEquivalent:@"v"];
    [editMenu addItemWithTitle:@"Delete"
                        action:@selector(delete:)
                 keyEquivalent:@""];
    [editMenu addItem:[NSMenuItem separatorItem]];
    [editMenu addItemWithTitle:@"Select All"
                        action:@selector(selectAll:)
                 keyEquivalent:@"a"];
    editMenuItem.submenu = editMenu;

    NSApp.mainMenu = mainMenu;
}

- (void)applicationWillTerminate:(NSNotification *)notification {
    if (self.serverTask && self.serverTask.isRunning) {
        [self.serverTask terminate];
    }
}

- (void)startServer {
    NSString *resourcePath = [[NSBundle mainBundle] resourcePath];
    NSString *appPath = [resourcePath stringByAppendingPathComponent:@"app"];
    NSString *serverPath = [appPath stringByAppendingPathComponent:@"server.py"];

    self.serverTask = [[NSTask alloc] init];
    self.serverTask.executableURL = [NSURL fileURLWithPath:@"/usr/bin/python3"];
    self.serverTask.arguments = @[serverPath];
    self.serverTask.currentDirectoryURL = [NSURL fileURLWithPath:appPath];

    NSMutableDictionary *environment = [[[NSProcessInfo processInfo] environment] mutableCopy];
    environment[@"FORMYDJ_NO_BROWSER"] = @"1";
    environment[@"FORMYDJ_PORT"] = @"8765";
    self.serverTask.environment = environment;

    NSPipe *outputPipe = [NSPipe pipe];
    self.serverTask.standardOutput = outputPipe;
    self.serverTask.standardError = outputPipe;

    NSError *error = nil;
    [self.serverTask launchAndReturnError:&error];
    if (error) {
        [self showError:[NSString stringWithFormat:@"Could not start ForMyDJ engine: %@", error.localizedDescription]];
    }
}

- (void)buildWindow {
    NSRect frame = NSMakeRect(0, 0, 1080, 720);
    self.window = [[NSWindow alloc] initWithContentRect:frame
                                              styleMask:(NSWindowStyleMaskTitled |
                                                         NSWindowStyleMaskClosable |
                                                         NSWindowStyleMaskMiniaturizable |
                                                         NSWindowStyleMaskResizable)
                                                backing:NSBackingStoreBuffered
                                                  defer:NO];
    self.window.title = @"ForMyDJ";
    [self.window center];

    WKWebViewConfiguration *configuration = [[WKWebViewConfiguration alloc] init];
    self.webView = [[WKWebView alloc] initWithFrame:self.window.contentView.bounds configuration:configuration];
    self.webView.navigationDelegate = self;
    self.webView.autoresizingMask = NSViewWidthSizable | NSViewHeightSizable;
    [self.window.contentView addSubview:self.webView];
    [self.window makeKeyAndOrderFront:nil];
    [NSApp activateIgnoringOtherApps:YES];
}

- (void)loadAppAfterDelay {
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(0.8 * NSEC_PER_SEC)), dispatch_get_main_queue(), ^{
        [self loadApp];
    });
}

- (void)loadApp {
    self.loadAttempts += 1;
    NSURL *url = [NSURL URLWithString:@"http://127.0.0.1:8765"];
    [self.webView loadRequest:[NSURLRequest requestWithURL:url]];
}

- (void)webView:(WKWebView *)webView didFailNavigation:(WKNavigation *)navigation withError:(NSError *)error {
    [self retryLoadIfNeeded];
}

- (void)webView:(WKWebView *)webView didFailProvisionalNavigation:(WKNavigation *)navigation withError:(NSError *)error {
    [self retryLoadIfNeeded];
}

- (void)retryLoadIfNeeded {
    if (self.loadAttempts >= 20) {
        [self showError:@"The ForMyDJ window opened, but the local engine did not respond. Close and reopen ForMyDJ."];
        return;
    }

    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(0.5 * NSEC_PER_SEC)), dispatch_get_main_queue(), ^{
        [self loadApp];
    });
}

- (void)showError:(NSString *)message {
    NSAlert *alert = [[NSAlert alloc] init];
    alert.messageText = @"ForMyDJ";
    alert.informativeText = message;
    [alert addButtonWithTitle:@"OK"];
    [alert runModal];
}

@end

int main(int argc, const char * argv[]) {
    @autoreleasepool {
        NSApplication *app = [NSApplication sharedApplication];
        AppDelegate *delegate = [[AppDelegate alloc] init];
        app.delegate = delegate;
        [app run];
    }
    return 0;
}

M

/usr/bin/clang -fobjc-arc -arch arm64 -mmacosx-version-min=12.0 "$LAUNCHER_M" -framework Cocoa -framework WebKit -o "$MACOS/ForMyDJ"
rm -f "$LAUNCHER_C" "$LAUNCHER_M"

echo "Built $APP"
