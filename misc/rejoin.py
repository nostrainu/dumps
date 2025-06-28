#grant rejoin tool
#please donate

# --------------------------- CONFIG --------------------------- #
CONFIG_FILE     = "rejoin_grant.json"      # auto-saved settings
CHECK_INTERVAL  = 20                       # seconds between package scans
FAST_POLL       = 1                        # seconds between stop-flag polls
# -------------------------------------------------------------- #

import subprocess, time, requests, colorsys, threading, sys
import urllib.parse, os, tempfile, shlex, json, re

# --------------------------- Globals -------------------------- #
place_id   = ""       # Roblox place ID
priv_code  = None     # VIP / share code
is_share   = False    # True if new share?code=… format
webhook    = ""       # Discord webhook URL

# ----------------------- Terminal helpers --------------------- #
sh   = lambda c: subprocess.getoutput(c).strip()
send = lambda m: requests.post(webhook, json={"content": m}, timeout=10) \
                   if webhook else None

# ----------------------------- Banner ------------------------- #
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
        print("".join(rgb(*(int(x*255) for x
                           in colorsys.hsv_to_rgb(i/len(ln),1,1)), ch)
                      for i, ch in enumerate(ln)))
    pad = (len(art[0]) - len("Made by Your Mom")) // 2
    print(" " * pad + rgb(255,255,255,"Made by Your Mom") + "\n")

# -------------------------- Config helpers -------------------- #
def load_config():
    global place_id, priv_code, is_share, webhook
    try:
        with open(CONFIG_FILE, "r") as f:
            cfg = json.load(f)
        place_id  = cfg.get("place_id",  "")
        priv_code = cfg.get("priv_code", None)
        is_share  = cfg.get("is_share", False)
        webhook   = cfg.get("webhook",  "")
        print(f"[Loaded config from {CONFIG_FILE}]")
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"[Config load error: {e}]")

def save_config():
    cfg = {
        "place_id" : place_id,
        "priv_code": priv_code,
        "is_share" : is_share,
        "webhook"  : webhook
    }
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=2)
        print(f"[Saved to {CONFIG_FILE}]")
    except Exception as e:
        print(f"[Config save error: {e}]")

def clear_config():
    global place_id, priv_code, is_share, webhook
    if os.path.exists(CONFIG_FILE):
        try: os.remove(CONFIG_FILE)
        except: pass
    place_id = ""; priv_code = None; is_share = False; webhook = ""
    print("[Config cleared]")

# -------------------------- Menu UI --------------------------- #
def show_menu():
    width = 57
    pad = lambda t: t + " " * (width - len(t))
    print("\n".join([
        "╔" + "═" * width + "╗",
        "║" + "ROLOBOX REJOIN MENU".center(width) + "║",
        "╠" + "═" * width + "╣",
        "║" + pad("  1. Game to Join") + "║",
        "║" + pad("  2. Start Auto-Join") + "║",
        "║" + pad("  3. Auto-Execute") + "║",
        "║" + pad("  4. Discord Webhook") + "║",
        "║" + pad("  5. Config (save / clear)") + "║",
        "║" + pad("  0. Exit (or type 'stop' anytime)") + "║",
        "║" + " " * width + "║",  
        "║" + pad("  Note: Hello! ") + "║",
        "╚" + "═" * width + "╝"
    ]))

# ----------------------- Roblox helpers ----------------------- #
pkgs   = lambda: [l.replace("package:","") for l in sh("pm list packages").splitlines()
                  if "com.roblox." in l]
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
    for p in ("/storage/emulated/0/Delta/Autoexecute", "/sdcard/Delta/Autoexecute"):
        if os.path.isdir(p): return p
    for root, dirs, _ in os.walk("/storage"):
        if "Delta" in dirs:
            path = os.path.join(root, "Delta", "Autoexecute")
            if os.path.isdir(path): return path
        if root.count(os.sep) > 6: dirs[:] = []
    return None

# ----------------------- stop listener ------------------------ #
def start_listener(flag):
    def _listen():
        for ln in sys.stdin:
            if ln.strip().lower() == "stop":
                flag["stop"] = True; break
    threading.Thread(target=_listen, daemon=True).start()

# --------------------------- Helpers -------------------------- #
def valid_webhook(url):
    return re.match(r"^https://(discord(app)?\.com)/api/webhooks/\d+/.+", url)

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
                pid = input(f"Place Id [{place_id or 'none'}]: ").strip()
                if not pid:
                    pid = place_id  # keep old
                if pid.isdigit() and input("Confirm (Y/N) ").lower() == "y":
                    place_id = pid; break
                print("  digits only.")
            while True:
                link = input("Private-server link (Enter to skip): ").strip()
                if not link:
                    priv_code = None; is_share = False; break
                parsed = urllib.parse.urlparse(link)
                q = urllib.parse.parse_qs(parsed.query)
                if "code" in q and "share" in parsed.path:
                    priv_code = q["code"][0]; is_share = True
                    if input("Confirm link (Y/N) ").lower() == "y": break
                elif "privateServerLinkCode" in q:
                    priv_code = q["privateServerLinkCode"][0]; is_share = False
                    if input("Confirm link (Y/N) ").lower() == "y": break
                else: print("  invalid link")
            print("Game info saved in memory.\n")

        # 2 ── Start Auto-Join
        elif choice == "2":
            if not place_id:
                print("Set Place Id first (option 1)."); continue
            stop_data = {"stop": False}
            start_listener(stop_data)
            send("VM Rejoin Tool **online** :satellite:")
            launched, last_check = set(), 0
            open_game(deep_link(place_id, priv_code, is_share))
            while not stop_data["stop"]:
                if time.time() - last_check >= CHECK_INTERVAL:
                    for p in pkgs():
                        if running(p):
                            launched.add(p)
                        else:
                            if p not in launched:
                                send(f"`{p}` closed — restarting :rocket:")
                            fstop(p); time.sleep(2)
                            open_game(deep_link(place_id, priv_code, is_share))
                            launched.add(p)
                    last_check = time.time()
                time.sleep(FAST_POLL)
            send("VM Rejoin Tool **stopped** :stop_sign:")
            print("\nStopped.\n")

        # 3 ── Auto-Execute 
        elif choice == "3":
            if not (delta := find_delta_autoexec()):
                print("Delta Autoexecute folder not found."); continue
            code = input("Loadstring: ").strip()
            if not code.startswith("loadstring"): continue
            dst = input("File name (myscript.txt): ").strip() or "myscript.txt"
            if not dst.endswith(".txt"): dst += ".txt"
            with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
                tmp.write(code); tmpf = tmp.name
            cmd = f'su -c "mv {shlex.quote(tmpf)} {shlex.quote(os.path.join(delta,dst))}"'
            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if proc.returncode: print(proc.stderr.strip())
            else: print("Saved to Delta Autoexecute.\n")

        # 4 ── Discord Webhook
        elif choice == "4":
            print(f"Current webhook: {webhook or '[none]'}")
            print("[1] Set new  [2] Clear  [0] Back")
            sub = input("> ").strip()
            if sub == "1":
                url = input("Paste Discord webhook URL: ").strip()
                if valid_webhook(url):
                    webhook = url
                    print("Webhook set.\n")
                    send("✅ Webhook updated & working!")
                else:
                    print("Invalid Discord webhook.\n")
            elif sub == "2":
                webhook = ""; print("Webhook cleared.\n")

        # 5 ── Config 
        elif choice == "5":
            print("[S] Save  [C] Clear  [0] Back")
            sub = input("> ").strip().lower()
            if sub == "s":
                save_config()
            elif sub == "c":
                if input("Sure? Y/N ").lower() == "y":
                    clear_config()

        # 0 ── Exit
        elif choice == "0":
            break
        else:
            print("Invalid choice.\n")

if __name__ == "__main__":
    main()
