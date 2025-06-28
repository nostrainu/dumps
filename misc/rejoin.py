#!/usr/bin/env python
# grant rejoin tool – public beta
# please donate ❤  (GCash / PayPal)

__version__ = "2.8"

RAW_URL = ("https://raw.githubusercontent.com/nostrainu/dumps/"
           "refs/heads/main/misc/rejoin.py")

# --------------------------- CONFIG --------------------------- #
CONFIG_FILE     = "rejoin_grant.json"      # auto‑saved settings
CHECK_INTERVAL  = 20                       # seconds between package scans
FAST_POLL       = 1                        # seconds between stop‑flag polls
# -------------------------------------------------------------- #

import subprocess, time, requests, colorsys, threading, sys
import urllib.parse, os, tempfile, shlex, json, re, shutil, tempfile as _tmp

# ------------------------ SELF‑UPDATER ------------------------ #
def check_self_update():
    try:
        r = requests.get(RAW_URL, timeout=10)
        r.raise_for_status()
        remote = r.text
        m = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', remote)
        if not m or m.group(1).strip() == __version__:
            return
        print(f"[Updater] New version {m.group(1)} available – updating…")
        cur = os.path.realpath(__file__)
        with _tmp.NamedTemporaryFile("w", delete=False,
                                     dir=os.path.dirname(cur)) as t:
            t.write(remote)
            new_path = t.name
        shutil.move(new_path, cur)
        print("[Updater] Update complete. Restarting…\n")
        os.execv(sys.executable, [sys.executable] + sys.argv)
    except Exception as e:
        print(f"[Updater] skipped ({e})")
check_self_update()

# --------------------------- GLOBALS -------------------------- #
place_id   = ""       # Roblox place ID
priv_code  = None     # VIP / share code
is_share   = False    # True if new share?code=… format
webhook    = ""       # Discord webhook URL

# ----------------------- TERMINAL HELPERS --------------------- #
sh   = lambda c: subprocess.getoutput(c).strip()
send = lambda m: requests.post(webhook, json={"content": m}, timeout=10) \
                   if webhook else None

# --------------------------- Banner --------------------------- #
def rgb(r,g,b,t): return f"\033[38;2;{r};{g};{b}m{t}\033[0m"
def banner():
    art = [
        "███╗   ██╗██╗ ██████╗ ██████╗  █████╗ ███╗   ██╗████████╗",
        "████╗  ██║██║██╔════╝ ██╔══██╗██╔══██╗████╗  ██║╚══██╔══╝",
        "██╔██╗ ██║██║██║  ███╗██████╔╝███████║██╔██╗ ██║   ██║   ",
        "██║╚██╗██║██║██║   ██║██╔══██╗██╔══██║██║╚██╗██║   ██║   ",
        "██║ ╚████║██║╚██████╔╝██║  ██║██║  ██║██║ ╚████║   ██║   ",
        "╚═╝  ╚═══╝╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝   ",
    ]
    for ln in art:
        print("".join(
            rgb(*(int(c*255) for c in colorsys.hsv_to_rgb(i/len(ln),1,1)), ch)
            for i, ch in enumerate(ln)))
    pad = (len(art[0]) - len("Made by Grant")) // 2
    print(" " * pad + rgb(255,255,255,"Made by Grant") + "\n")

# ----------------------- CONFIG HELPERS ----------------------- #
def load_config():
    global place_id, priv_code, is_share, webhook
    try:
        with open(CONFIG_FILE, "r") as f:
            cfg = json.load(f)
        place_id  = cfg.get("place_id", "")
        priv_code = cfg.get("priv_code")
        is_share  = cfg.get("is_share", False)
        webhook   = cfg.get("webhook", "")
        print(f"[Loaded config from {CONFIG_FILE}]")
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"[Config load error: {e}]")

def save_config():
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(
                dict(place_id=place_id, priv_code=priv_code,
                     is_share=is_share, webhook=webhook), f, indent=2)
        print(f"[Saved to {CONFIG_FILE}]")
    except Exception as e:
        print(f"[Config save error: {e}]")

def clear_config():
    global place_id, priv_code, is_share, webhook
    try:
        if os.path.exists(CONFIG_FILE):
            os.remove(CONFIG_FILE)
    except: pass
    place_id = ""; priv_code = None; is_share = False; webhook = ""
    print("[Config cleared]")

# -------------------------- MENU UI --------------------------- #
def show_menu():
    width = 57
    bold = "\033[1m"
    gray = "\033[90m"
    reset = "\033[0m"

    def strip_ansi(s):
        return re.sub(r'\033\[[0-9;]*m', '', s)

    def pad(text):
        visible_len = len(strip_ansi(text))
        return text + " " * (width - visible_len)

    def border(left, right, fill="═"):
        return left + fill * width + right

    def line(text, color=""):
        return "║" + color + pad(text) + reset + "║"

    print("\n".join([
        border("╔", "╗"),
        line(bold + "ROLOBOX REJOIN MENU".center(width) + reset),
        border("╠", "╣"),
        line("  [1] Game to Join"),
        line("  [2] Start Auto-Join"),
        line("  [3] Auto-Execute"),
        line("  [4] Discord Webhook"),
        line("  [5] Config"),
        line("  [6] Check for Updates"),
        line("  [0] Exit"),
        line(""),
        border("╠", "╣"),
        "║" + pad(gray + "  Tip: Type 'stop' anytime to cancel rejoining" + reset) + "║",
        border("╚", "╝")
    ]))

# ----------------------- ROBLOX HELPERS ----------------------- #
pkgs   = lambda: [l.replace("package:", "") for l in sh("pm list packages")
                  .splitlines() if "com.roblox." in l]
running = lambda p: p in sh("dumpsys window | grep mCurrentFocus") \
                 or sh(f"pidof {p}") or p in sh("ps -A")
fstop   = lambda p: sh(f"am force-stop {p}")

def deep_link(pid, code=None, is_share=False):
    if code:
        if is_share:
            return f"roblox://navigation/share_links?code={code}&type=Server"
        return f"roblox://experiences/start?placeId={pid}&linkCode={code}"
    return f"roblox://experiences/start?placeId={pid}"

open_game = lambda url: sh(f'am start -a android.intent.action.VIEW -d "{url}"')

def find_delta_autoexec():
    for p in ("/storage/emulated/0/Delta/Autoexecute",
              "/sdcard/Delta/Autoexecute"):
        if os.path.isdir(p): return p
    for root, dirs, _ in os.walk("/storage"):
        if "Delta" in dirs:
            path = os.path.join(root, "Delta", "Autoexecute")
            if os.path.isdir(path): return path
        if root.count(os.sep) > 6: dirs[:] = []
    return None

# ----------------------- STOP LISTENER ------------------------ #
def start_listener(flag):
    def _listen():
        for ln in sys.stdin:
            if ln.strip().lower() == "stop":
                flag["stop"] = True; break
    threading.Thread(target=_listen, daemon=True).start()

# --------------------------- HELPERS -------------------------- #
valid_webhook = lambda url: re.match(
    r"^https://(discord(app)?\.com)/api/webhooks/\d+/.+", url)

# ---------------------------- MAIN ---------------------------- #
def main():
    global place_id, priv_code, is_share, webhook
    banner()
    load_config()

    while True:
        show_menu()
        choice = input("Choose Number: ").strip()

        # 1 ── Game to Join
        if choice == "1":
            while True:
                pid = input(f"Place Id [{place_id or 'none'}]: ").strip() or place_id
                if pid.isdigit() and input("Confirm (Y/N) ").lower() == "y":
                    place_id = pid; break
                print("  digits only.")
            while True:
                link = input("Private‑server link (Enter to skip): ").strip()
                if not link:
                    priv_code = None; is_share = False; break
                p = urllib.parse.urlparse(link)
                q = urllib.parse.parse_qs(p.query)
                if "code" in q and "share" in p.path:
                    priv_code = q["code"][0]; is_share = True
                    if input("Confirm link? (Y/N) ").lower() == "y":
                        break
                elif "privateServerLinkCode" in q:
                    priv_code = q["privateServerLinkCode"][0]; is_share = False
                    if input("Confirm link? (Y/N) ").lower() == "y":
                        break
                else:
                    print("  invalid link")
            print("Game info saved in memory.\n")

        # 2 ── Auto‑Join Menu
        elif choice == "2":
            if not place_id:
                print("Set Place Id first (option 1).\n")
                continue

            while True:
                print("\nAuto‑Join:")
                print(f"[1] Start  (default interval = {CHECK_INTERVAL}s)")
                print("[2] Interval (set custom)")
                print("[0] Back")
                sub = input("> ").strip()

                if sub == "0":
                    break

                if sub == "1":
                    interval = CHECK_INTERVAL
                    print(f"Starting Auto‑Join every {interval}s…")

                elif sub == "2":
                    try:
                        raw = input("Interval in seconds: ").strip()
                        interval = int(raw)
                        if interval <= 0:
                            print("Interval must be > 0.\n")
                            continue
                    except ValueError:
                        print("Invalid number.\n")
                        continue

                    if input(f"Start Auto‑Join every {interval}s? (Y/N): "
                             ).lower() != "y":
                        print("Cancelled. Returning…\n")
                        continue
                else:
                    print("Invalid choice.\n")
                    continue
                           
                for pkg in pkgs():
                    if running(pkg):
                        sh(f"su -c 'am force-stop {pkg}'")
                time.sleep(1)

                stop = {"stop": False}
                start_listener(stop)
                send("VM Rejoin Tool **online** :satellite:")
                launched, last = set(), 0
                open_game(deep_link(place_id, priv_code, is_share))

                while not stop["stop"]:
                    if time.time() - last >= interval:
                        for p in pkgs():
                            if running(p):
                                launched.add(p)
                            else:
                                if p not in launched:
                                    send(f"`{p}` closed — restarting :rocket:")
                                sh(f"su -c 'am force-stop {p}'")
                                time.sleep(2)
                                open_game(deep_link(place_id, priv_code, is_share))
                                launched.add(p)
                        last = time.time()
                    time.sleep(FAST_POLL)

                send("VM Rejoin Tool **stopped** :stop_sign:")
                print("\nStopped. Returning to menu…\n")
                break
                       
        # 3 ── Auto‑Execute
        elif choice == "3":
            print("Executor:")
            print("[1] Delta   [2] KRNL   [0] Back")
            ex = input("> ").strip()
            if ex == "0":
                continue
            if ex not in ("1", "2"):
                print("Invalid executor.\n")
                continue

            root_name = "Delta" if ex == "1" else "krnl"
            auto_path = find_delta_autoexec() if ex == "1" else None
            if not auto_path:
                print(f"{root_name} Autoexec folder not found.\n")
                continue

            while True:
                print("Loadstring:")
                print("[1] Add   [2] Delete   [0] Back")
                sub = input("> ").strip()
                if sub == "0":
                    break
                elif sub == "1":
                    code = input("Loadstring: ").strip()
                    if not code.startswith("loadstring"):
                        print("Must start with loadstring\n")
                        continue
                    if input("Confirm Y/N: ").lower() != "y":
                        continue

                    fname = input("File name (without .txt): ").strip()
                    if not fname:
                        print("Cancelled.\n"); continue
                    if not fname.lower().endswith(".txt"):
                        fname += ".txt"
                    if input(f"Save as {fname}? Y/N: ").lower() != "y":
                        continue

                    with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
                        tmp.write(code); tmpf = tmp.name
                    dst = os.path.join(auto_path, fname)
                    cmd = f'su -c "mv {shlex.quote(tmpf)} {shlex.quote(dst)}"'
                    prc = subprocess.run(cmd, shell=True,
                                         capture_output=True, text=True)
                    if prc.returncode:
                        print(prc.stderr.strip())
                    else:
                        print(f"Saved to {root_name}/Autoexec: {fname}\n")
                        break
                elif sub == "2":
                    files = sorted([f for f in os.listdir(auto_path)
                                    if f.lower().endswith(".txt")])
                    if not files:
                        print("No .txt files in Autoexec.\n")
                        continue

                    print("\nDelete Files:")
                    for i, f in enumerate(files, 1):
                        print(f"[{i}] {f}")
                    print("[0] Delete ALL")
                    pick = input("> ").strip()
                    if not pick.isdigit():
                        print("Invalid input.\n"); continue

                    if pick == "0":
                        if input("Delete ALL files? Y/N: ").lower() != "y":
                            continue
                        targets = files
                    else:
                        idx = int(pick) - 1
                        if idx < 0 or idx >= len(files):
                            print("Invalid choice.\n"); continue
                        targets = [files[idx]]

                    err = False
                    for f in targets:
                        path = os.path.join(auto_path, f)
                        cmd = f'su -c "rm -f {shlex.quote(path)}"'
                        if subprocess.run(cmd, shell=True).returncode != 0:
                            err = True
                    if err:
                        print("Some files could not be deleted.\n")
                    else:
                        print("Deletion complete.\n")
                else:
                    print("Invalid choice.\n")

        # 4 ── Discord Webhook
        elif choice == "4":
            print(f"Current webhook: {webhook or '[none]'}")
            print("[1] Set new  [2] Clear  [0] Back")
            sub = input("> ").strip()
            if sub == "1":
                url = input("Paste Discord webhook URL: ").strip()
                if valid_webhook(url):
                    webhook = url; print("Webhook set.\n"); send("✅ Webhook updated!")
                else:
                    print("Invalid Discord webhook.\n")
            elif sub == "2":
                webhook = ""; print("Webhook cleared.\n")

        # 5 ── Config
        elif choice == "5":
            print("[1] Save  [2] Clear  [0] Back")
            sub = input("> ").strip().lower()
            if sub == "1":
                save_config()
            elif sub == "2" and input("Sure? Y/N ").lower() == "y":
                clear_config()

        # 6 ── Check for Updates
        elif choice == "6":
            try:
                print("[Update] Checking GitHub…")
                r = requests.get(RAW_URL, timeout=10)
                r.raise_for_status()
                remote_code = r.text
                m = re.search(r'__version__\s*=\s*[\'"]([^\'"]+)[\'"]',
                              remote_code)
                remote_ver = m.group(1).strip() if m else None
                if not remote_ver:
                    print("[Update] Remote file missing __version__; abort.\n")
                    continue
                if remote_ver == __version__:
                    print(f"[Update] You’re already on the latest "
                          f"version (v{__version__}).\n")
                    continue

                print(f"[Update] New version v{remote_ver} found. Downloading…")
                resp = requests.get(RAW_URL, stream=True, timeout=10)
                resp.raise_for_status()
                total = int(resp.headers.get("Content-Length", 0))
                if total == 0:
                    print("[Update] Unable to get file size, downloading anyway…")

                cur_path = os.path.realpath(__file__)
                dir_path = os.path.dirname(cur_path)
                bar_len = 40
                downloaded = 0
                chunk_size = 8192

                with _tmp.NamedTemporaryFile("wb", delete=False,
                                             dir=dir_path) as tmp:
                    for chunk in resp.iter_content(chunk_size=chunk_size):
                        if not chunk:
                            continue
                        tmp.write(chunk)
                        downloaded += len(chunk)
                        if total:
                            filled = int(bar_len * downloaded // total)
                            pct = downloaded / total * 100
                            bar = "█" * filled + "-" * (bar_len - filled)
                            sys.stdout.write(f"\r  [{bar}] {pct:6.2f}%")
                            sys.stdout.flush()
                    tmp_path = tmp.name

                if total:
                    sys.stdout.write("\r  [████████████████████████████████████████] 100.00%\n")
                print("[Update] Download complete. Installing…")

                shutil.move(tmp_path, cur_path)
                print(f"[Update] Installed v{remote_ver}. Restarting script…\n")
                time.sleep(1)
                os.execv(sys.executable, [sys.executable] + sys.argv)

            except Exception as e:
                print(f"[Update error] {e}\n")

        # 0 ── Exit
        elif choice == "0":
            break
        else:
            print("Invalid choice.\n")

if __name__ == "__main__":
    main()
