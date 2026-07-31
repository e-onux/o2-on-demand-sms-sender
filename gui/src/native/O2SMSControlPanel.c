#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

/*
 * Native macOS launcher for the Tkinter control panel.
 *
 * LaunchServices expects an application bundle's main executable to be a
 * Mach-O binary.  The launcher redirects diagnostics to the project's data
 * directory, removes the bundle identifier inherited from Finder (Tk creates
 * its own application identity), then replaces itself with Python.
 */

static const char *PROJECT_DIR =
    "/Users/emironuk/Documents/Projeler/01_Kisisel_Projeler/o2-on-demand-sms-sender";
static const char *SCRIPT_PATH =
    "/Users/emironuk/Documents/Projeler/01_Kisisel_Projeler/o2-on-demand-sms-sender/gui/src/control_panel.py";
static const char *LOG_PATH =
    "/Users/emironuk/Documents/Projeler/01_Kisisel_Projeler/o2-on-demand-sms-sender/data/control_panel.log";

static void redirect_output(void) {
    int log_fd = open(LOG_PATH, O_WRONLY | O_CREAT | O_APPEND, 0644);
    if (log_fd < 0) {
        return;
    }
    (void)dup2(log_fd, STDOUT_FILENO);
    (void)dup2(log_fd, STDERR_FILENO);
    close(log_fd);
}

static void run_python(const char *python_path) {
    char *const arguments[] = {
        (char *)python_path,
        (char *)SCRIPT_PATH,
        NULL,
    };
    execv(python_path, arguments);
}

int main(void) {
    (void)mkdir("/Users/emironuk/Documents/Projeler/01_Kisisel_Projeler/o2-on-demand-sms-sender/data", 0755);
    redirect_output();

    if (chdir(PROJECT_DIR) != 0) {
        dprintf(STDERR_FILENO, "Project directory cannot be opened: %s\n", strerror(errno));
        return 1;
    }

    unsetenv("__CFBundleIdentifier");
    unsetenv("PYTHONHOME");
    setenv("PATH", "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin", 1);

    run_python("/opt/homebrew/opt/python@3.13/libexec/bin/python3");
    dprintf(STDERR_FILENO, "Homebrew Python could not start: %s\n", strerror(errno));

    run_python("/usr/bin/python3");
    dprintf(STDERR_FILENO, "System Python could not start: %s\n", strerror(errno));
    return 127;
}
