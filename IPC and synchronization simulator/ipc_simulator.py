"""
IPC & SYNC ARCADE - Interprocess Communication and Synchronization Simulator
=============================================================================
A Pac-Man themed, educational, fully integrated Operating Systems simulation suite.
Unified 6-Module OS Simulation with deep-dive IPC & Process Synchronization.

Author: IPC Group
Platform: Python 3 with Tkinter (Zero external dependencies)
Theme: Classic 1980s Retro Arcade / Pac-Man Neon Theme
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import math
import random
from datetime import datetime
from collections import deque
from typing import Optional, List, Dict, Tuple

# Try importing winsound on Windows for authentic 8-bit retro arcade sounds
try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False


# ─────────────────────────────────────────────────────────────────────────────
# 1. ARCADE THEME CONSTANTS & PALETTE
# ─────────────────────────────────────────────────────────────────────────────
BG_DARK        = "#080816"       # Deep arcade cabinet black
BG_PANEL       = "#0d0d26"       # Dark navy sidebars and topbars
BG_CARD        = "#141432"       # Card background
BG_CARD_LIGHT  = "#1c1c44"       # Highlighted card background
NEON_YELLOW    = "#FFD700"       # Pac-Man classic yellow
NEON_BLUE      = "#00E5FF"       # Cyan tube & Inky cyan
NEON_PINK      = "#FF4081"       # Pinky pink
NEON_RED       = "#FF1744"       # Blinky red & blocked warnings
NEON_ORANGE    = "#FF9100"       # Clyde orange
NEON_GREEN     = "#00E676"       # Mutex unlocked / success green
NEON_PURPLE    = "#D500F9"       # Module accents
TEXT_WHITE     = "#F0F4FF"       # Crisp high-contrast text
TEXT_DIM       = "#7C8BA1"       # Secondary hints
MAZE_BLUE      = "#1A237E"       # Classic arcade maze wall color

FONT_TITLE     = ("Courier New", 26, "bold")
FONT_HEADER    = ("Courier New", 15, "bold")
FONT_SUBHEADER = ("Courier New", 12, "bold")
FONT_BODY      = ("Courier New", 10, "bold")
FONT_SMALL     = ("Courier New", 8, "bold")
FONT_CODE      = ("Consolas", 9, "bold")
FONT_HUGE      = ("Courier New", 36, "bold")


# ─────────────────────────────────────────────────────────────────────────────
# 2. RETRO ARCADE SOUND ENGINE
# ─────────────────────────────────────────────────────────────────────────────
class SoundManager:
    """Non-blocking 8-bit retro sound engine using native Windows sound."""

    def __init__(self):
        self.enabled = True

    def _play_tone(self, freq: int, duration_ms: int):
        if not self.enabled or not HAS_WINSOUND:
            return
        def run():
            try:
                winsound.Beep(freq, duration_ms)
            except Exception:
                pass
        threading.Thread(target=run, daemon=True).start()

    def play_send(self):
        """Pac-Man chomp/dispatch chirp."""
        if not self.enabled or not HAS_WINSOUND:
            return
        def run():
            try:
                winsound.Beep(587, 50)
                winsound.Beep(880, 60)
            except Exception:
                pass
        threading.Thread(target=run, daemon=True).start()

    def play_receive(self):
        """Ghost consume / pellet eat tone."""
        if not self.enabled or not HAS_WINSOUND:
            return
        def run():
            try:
                winsound.Beep(740, 50)
                winsound.Beep(440, 70)
            except Exception:
                pass
        threading.Thread(target=run, daemon=True).start()

    def play_blocked(self):
        """Low warning buzz when blocked."""
        if not self.enabled or not HAS_WINSOUND:
            return
        def run():
            try:
                winsound.Beep(220, 140)
            except Exception:
                pass
        threading.Thread(target=run, daemon=True).start()

    def play_success(self):
        """Ascending arcade fanfare."""
        if not self.enabled or not HAS_WINSOUND:
            return
        def run():
            try:
                for f in [523, 659, 784, 1046]:
                    winsound.Beep(f, 60)
            except Exception:
                pass
        threading.Thread(target=run, daemon=True).start()

    def play_quiz_wrong(self):
        """Descending buzz for quiz mistake."""
        if not self.enabled or not HAS_WINSOUND:
            return
        def run():
            try:
                winsound.Beep(330, 80)
                winsound.Beep(260, 120)
            except Exception:
                pass
        threading.Thread(target=run, daemon=True).start()

    def toggle(self) -> bool:
        self.enabled = not self.enabled
        return self.enabled


SOUND_ENGINE = SoundManager()


# ─────────────────────────────────────────────────────────────────────────────
# 3. DATA STRUCTURES & SYNCHRONIZATION PRIMITIVES
# ─────────────────────────────────────────────────────────────────────────────

class MessagePacket:
    """Represents a structured IPC message packet/envelope."""

    def __init__(self, msg_id: int, sender: str, receiver: str,
                 msg_type: str, payload: str, icon: str = "🟡", priority: int = 1):
        self.msg_id = msg_id
        self.sender = sender
        self.receiver = receiver
        self.msg_type = msg_type
        self.payload = payload
        self.icon = icon
        self.priority = priority
        self.timestamp = datetime.now().strftime("%H:%M:%S")
        self.size_bytes = len(payload.encode('utf-8')) + 16

    def short_display(self) -> str:
        text = self.payload if len(self.payload) <= 8 else self.payload[:7] + "…"
        return f"{self.icon} {text}"


class BoundedBufferQueue:
    """
    Classic OS Bounded Buffer backed by Dijkstra's Three-Semaphore synchronization:
      1. mutex: Binary semaphore protecting critical section (0 or 1)
      2. empty_sem: Counting semaphore tracking empty slots (init N)
      3. full_sem: Counting semaphore tracking occupied slots (init 0)
    """

    def __init__(self, capacity: int = 5):
        self.capacity = max(1, min(10, capacity))
        self._buffer: List[Optional[MessagePacket]] = [None] * self.capacity
        self.head = 0       # Read index (consumer)
        self.tail = 0       # Write index (producer)
        self.count = 0      # Current number of items
        self.lock = threading.Lock()

        # OS Semaphore Models
        self.mutex = 1
        self.empty_sem = self.capacity
        self.full_sem = 0

    def resize(self, new_cap: int):
        with self.lock:
            new_cap = max(1, min(10, new_cap))
            if new_cap == self.capacity:
                return

            # Extract existing items in FIFO order
            items = []
            while self.count > 0 and len(items) < new_cap:
                items.append(self._buffer[self.head])
                self.head = (self.head + 1) % self.capacity
                self.count -= 1

            self.capacity = new_cap
            self._buffer = [None] * new_cap
            for i, it in enumerate(items):
                self._buffer[i] = it
            self.head = 0
            self.tail = len(items) % new_cap
            self.count = len(items)

            # Update semaphores to reflect new size
            self.empty_sem = self.capacity - self.count
            self.full_sem = self.count

    def enqueue(self, packet: MessagePacket) -> Tuple[bool, str]:
        """
        Producer operation:
          wait(empty_sem)
          wait(mutex)
          buffer[tail] = packet
          signal(mutex)
          signal(full_sem)
        """
        with self.lock:
            if self.count >= self.capacity:
                return False, "Buffer is FULL (empty_sem == 0, producer blocked)"

            # Step 1: wait(empty_sem)
            self.empty_sem -= 1

            # Step 2: wait(mutex)
            self.mutex = 0

            # Step 3: Critical Section
            self._buffer[self.tail] = packet
            self.tail = (self.tail + 1) % self.capacity
            self.count += 1

            # Step 4: signal(mutex)
            self.mutex = 1

            # Step 5: signal(full_sem)
            self.full_sem += 1

            return True, "Enqueued successfully into mailbox slot"

    def dequeue(self) -> Tuple[Optional[MessagePacket], str]:
        """
        Consumer operation:
          wait(full_sem)
          wait(mutex)
          packet = buffer[head]
          signal(mutex)
          signal(empty_sem)
        """
        with self.lock:
            if self.count == 0:
                return None, "Buffer is EMPTY (full_sem == 0, consumer blocked)"

            # Step 1: wait(full_sem)
            self.full_sem -= 1

            # Step 2: wait(mutex)
            self.mutex = 0

            # Step 3: Critical Section
            packet = self._buffer[self.head]
            self._buffer[self.head] = None
            self.head = (self.head + 1) % self.capacity
            self.count -= 1

            # Step 4: signal(mutex)
            self.mutex = 1

            # Step 5: signal(empty_sem)
            self.empty_sem += 1

            return packet, "Dequeued successfully from mailbox slot"

    def peek_slots(self) -> List[Optional[MessagePacket]]:
        with self.lock:
            return list(self._buffer)

    @property
    def is_full(self) -> bool:
        with self.lock:
            return self.count >= self.capacity

    @property
    def is_empty(self) -> bool:
        with self.lock:
            return self.count == 0

    def clear(self):
        with self.lock:
            self._buffer = [None] * self.capacity
            self.head = 0
            self.tail = 0
            self.count = 0
            self.mutex = 1
            self.empty_sem = self.capacity
            self.full_sem = 0


class ProcessState:
    RUNNING   = "RUNNING"
    SENDING   = "SENDING"
    RECEIVING = "RECEIVING"
    BLOCKED   = "BLOCKED"
    WAITING   = "WAITING"


# ─────────────────────────────────────────────────────────────────────────────
# 4. GRAPHICAL HELPERS & PAC-MAN ART
# ─────────────────────────────────────────────────────────────────────────────

def draw_pacman(canvas: tk.Canvas, x: float, y: float, r: float,
                mouth_angle: float = 40, color: str = NEON_YELLOW,
                facing: str = "right", tag: str = "pacman"):
    """Draw an authentic Pac-Man with chomping mouth and eye."""
    canvas.delete(tag)
    if facing == "right":
        start = mouth_angle / 2
        extent = 360 - mouth_angle
        ex, ey = x + r * 0.15, y - r * 0.45
    elif facing == "left":
        start = 180 + mouth_angle / 2
        extent = 360 - mouth_angle
        ex, ey = x - r * 0.15, y - r * 0.45
    elif facing == "up":
        start = 90 + mouth_angle / 2
        extent = 360 - mouth_angle
        ex, ey = x - r * 0.45, y - r * 0.15
    else:  # down
        start = 270 + mouth_angle / 2
        extent = 360 - mouth_angle
        ex, ey = x + r * 0.45, y + r * 0.15

    # Main Body Arc
    canvas.create_arc(x - r, y - r, x + r, y + r,
                      start=start, extent=extent,
                      fill=color, outline=color, width=2, tags=tag)
    # Eye
    er = max(2.0, r * 0.12)
    canvas.create_oval(ex - er, ey - er, ex + er, ey + er,
                       fill="black", outline="black", tags=tag)


def draw_ghost(canvas: tk.Canvas, x: float, y: float, r: float = 26,
               color: str = NEON_PINK, look_dir: str = "left",
               scared: bool = False, tag: str = "ghost"):
    """Draw a classic arcade ghost with wavy skirt and pupils."""
    canvas.delete(tag)
    body_color = "#1E88E5" if scared else color
    eye_white = "#FFEB3B" if scared else "white"
    pupil_color = "#D50000" if scared else "#000080"

    # Head Dome
    canvas.create_arc(x - r, y - r, x + r, y + r,
                      start=0, extent=180,
                      fill=body_color, outline=body_color, tags=tag)
    # Middle Body
    canvas.create_rectangle(x - r, y, x + r, y + r * 1.25,
                             fill=body_color, outline=body_color, tags=tag)

    # Wavy bottom tentacles (3 waves)
    w_bump = (r * 2) / 3
    for i in range(3):
        bx = x - r + i * w_bump
        canvas.create_arc(bx, y + r * 0.9, bx + w_bump, y + r * 1.45,
                          start=0, extent=-180,
                          fill=BG_DARK, outline=BG_DARK, tags=tag)

    # Eyes
    eye_offset_x = -4 if look_dir == "left" else (4 if look_dir == "right" else 0)
    for side in [-1, 1]:
        ex = x + side * (r * 0.38)
        ey = y - r * 0.1
        canvas.create_oval(ex - r * 0.22, ey - r * 0.22,
                           ex + r * 0.22, ey + r * 0.22,
                           fill=eye_white, outline=eye_white, tags=tag)
        # Pupil
        px = ex + eye_offset_x * 0.8
        py = ey
        canvas.create_oval(px - r * 0.1, py - r * 0.1,
                           px + r * 0.1, py + r * 0.1,
                           fill=pupil_color, outline=pupil_color, tags=tag)


def neon_button(parent, text: str, command, color: str = NEON_YELLOW,
                width: int = 16, height: int = 1) -> tk.Button:
    """Arcade styled glowing button with active hover effects."""
    btn = tk.Button(
        parent, text=text, command=command,
        bg=BG_CARD, fg=color,
        activebackground=color, activeforeground=BG_DARK,
        font=FONT_BODY, relief="flat", bd=0,
        highlightthickness=2, highlightbackground=color,
        width=width, height=height, cursor="hand2",
        padx=4, pady=4
    )
    # Subtle hover glow
    btn.bind("<Enter>", lambda e: btn.config(bg=color, fg=BG_DARK))
    btn.bind("<Leave>", lambda e: btn.config(bg=BG_CARD, fg=color))
    return btn


def scrolled_text(parent, height: int = 8, width: int = 50) -> tk.Frame:
    """Arcade-styled terminal log container."""
    frame = tk.Frame(parent, bg=BG_CARD, bd=1, relief="flat",
                     highlightthickness=1, highlightbackground=NEON_BLUE)
    txt = tk.Text(frame, height=height, width=width,
                  bg=BG_CARD, fg=TEXT_WHITE, font=FONT_CODE,
                  insertbackground=NEON_YELLOW, relief="flat", bd=0,
                  state="disabled", wrap="word")
    sb = tk.Scrollbar(frame, orient="vertical", command=txt.yview,
                      bg=BG_DARK, troughcolor=BG_DARK,
                      activebackground=NEON_BLUE)
    txt.configure(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y")
    txt.pack(side="left", fill="both", expand=True)
    frame.txt = txt
    return frame


def append_text(widget: tk.Text, text: str):
    """Append text to a disabled text widget smoothly."""
    widget.configure(state="normal")
    widget.insert("end", text + "\n")
    widget.see("end")
    widget.configure(state="disabled")


# ─────────────────────────────────────────────────────────────────────────────
# 5. MODULE 1: IPC & SYNCHRONIZATION ARCADE (CORE ASSIGNED MODULE)
# ─────────────────────────────────────────────────────────────────────────────

class IPCSyncModule(tk.Frame):
    """
    Comprehensive interactive simulation demonstrating:
      1. Message Passing & Mailbox Buffer
      2. Send and Receive operations (Manual & Auto-Sim)
      3. Bounded-Buffer behavior (Full & Empty block states)
      4. Three-Semaphore synchronization (mutex, empty, full)
      5. Step-by-step Pseudocode tracer
      6. Interactive Game Learning: Challenge Missions & Quiz Arcade!
    """

    PELLET_PRESETS = [
        ("🟡 Power Pellet", "POWER_PELLET", "🟡"),
        ("🍒 Bonus Cherry", "CHERRY_FRUIT", "🍒"),
        ("🍓 Strawberry",   "STRAWBERRY",   "🍓"),
        ("⚡ Speed Pulse",   "SPEED_BOOST",   "⚡"),
        ("📡 Radar Signal",  "RADAR_SCAN",   "📡"),
        ("🔑 Secret Key",    "MAZE_KEY",     "🔑"),
    ]

    GHOST_TARGETS = [
        ("Blinky (Red - PROC-B1)",  "Blinky", NEON_RED),
        ("Pinky (Pink - PROC-B2)",   "Pinky",  NEON_PINK),
        ("Inky (Cyan - PROC-B3)",    "Inky",   NEON_BLUE),
        ("Clyde (Orange - PROC-B4)", "Clyde",  NEON_ORANGE),
    ]

    def __init__(self, parent, notify_home_cb=None):
        super().__init__(parent, bg=BG_DARK)
        self.notify_home = notify_home_cb

        # Data & synchronization state
        self.buffer = BoundedBufferQueue(capacity=5)
        self.msg_counter = 1
        self.sent_count = 0
        self.recv_count = 0

        # Process states
        self.proc_a_state = ProcessState.RUNNING
        self.proc_b_state = ProcessState.RUNNING

        # Animation state
        self._anim_id = None
        self._tick = 0
        self._pac_mouth = 0
        self._pac_dir = 1
        self._ghost_bob = 0
        self._ghost_dir = 1
        self._pellets_traveling: List[dict] = []

        # Auto-generation threads/flags
        self.auto_producer_active = False
        self.auto_consumer_active = False
        self._auto_prod_after_id = None
        self._auto_cons_after_id = None

        # Mission mode tracking
        self.mission_scores = 0
        self.mission_flags = {
            "m1_sent": 0,
            "m2_full_hit": False,
            "m3_empty_hit": False,
            "m4_balanced_ticks": 0
        }

        # Quiz State
        self.quiz_index = 0
        self.quiz_score = 0
        self.quiz_answered = False
        self._pending_afters: List = []

        self._build_ui()

    def _safe_after(self, ms: int, func):
        aid = None
        def wrapper():
            if aid in self._pending_afters:
                self._pending_afters.remove(aid)
            try:
                if self.winfo_exists():
                    func()
            except Exception:
                pass
        aid = self.after(ms, wrapper)
        self._pending_afters.append(aid)
        return aid

    def _build_ui(self):
        # ── Top Tab Bar: Sub-modes (Arena / Missions / Quiz / Concepts)
        tab_bar = tk.Frame(self, bg=BG_PANEL, pady=4)
        tab_bar.pack(fill="x")

        self.sub_mode_var = tk.StringVar(value="arena")
        sub_modes = [
            ("🕹️ SIMULATION ARENA", "arena"),
            ("🏆 CHALLENGE MISSIONS", "missions"),
            ("🧠 ARCADE QUIZ BATTLE", "quiz"),
            ("📖 OS CONCEPT GUIDE", "guide"),
        ]

        self.tab_buttons = {}
        for title, key in sub_modes:
            btn = tk.Button(
                tab_bar, text=title, font=FONT_BODY,
                bg=BG_CARD if key != "arena" else NEON_YELLOW,
                fg=NEON_YELLOW if key != "arena" else BG_DARK,
                activebackground=NEON_YELLOW, activeforeground=BG_DARK,
                relief="flat", bd=0, padx=12, pady=4, cursor="hand2",
                command=lambda k=key: self._switch_sub_tab(k)
            )
            btn.pack(side="left", padx=4)
            self.tab_buttons[key] = btn

        # Quick stats badge on the right of tab bar
        self.quick_stats_label = tk.Label(
            tab_bar, text="MAILBOX: 0/5 | MUTEX: 1 | EMPTY: 5 | FULL: 0",
            font=FONT_SMALL, bg=BG_PANEL, fg=NEON_GREEN
        )
        self.quick_stats_label.pack(side="right", padx=12)

        # ── Sub-tab Container
        self.sub_container = tk.Frame(self, bg=BG_DARK)
        self.sub_container.pack(fill="both", expand=True)

        # Sub-frames
        self.frame_arena = tk.Frame(self.sub_container, bg=BG_DARK)
        self.frame_missions = tk.Frame(self.sub_container, bg=BG_DARK)
        self.frame_quiz = tk.Frame(self.sub_container, bg=BG_DARK)
        self.frame_guide = tk.Frame(self.sub_container, bg=BG_DARK)

        self._build_arena_view()
        self._build_missions_view()
        self._build_quiz_view()
        self._build_guide_view()

        self._switch_sub_tab("arena")

    def _switch_sub_tab(self, key: str):
        self.sub_mode_var.set(key)
        for k, btn in self.tab_buttons.items():
            if k == key:
                btn.config(bg=NEON_YELLOW, fg=BG_DARK)
            else:
                btn.config(bg=BG_CARD, fg=NEON_YELLOW)

        # Hide all
        for f in [self.frame_arena, self.frame_missions, self.frame_quiz, self.frame_guide]:
            f.pack_forget()

        if key == "arena":
            self.frame_arena.pack(fill="both", expand=True)
        elif key == "missions":
            self.frame_missions.pack(fill="both", expand=True)
            self._update_mission_ui()
        elif key == "quiz":
            self.frame_quiz.pack(fill="both", expand=True)
            self._render_quiz_question()
        elif key == "guide":
            self.frame_guide.pack(fill="both", expand=True)

    # ═════════════════════════════════════════════════════════════════════════
    # SUB-TAB 1: SIMULATION ARENA VIEW
    # ═════════════════════════════════════════════════════════════════════════
    def _build_arena_view(self):
        root = self.frame_arena

        # 3 Columns: Left Controls (240px), Center Arena (Canvas + Tracer), Right Inspector & Semaphores (280px)
        left_col = tk.Frame(root, bg=BG_DARK, width=250)
        left_col.pack(side="left", fill="y", padx=(6, 4), pady=4)
        left_col.pack_propagate(False)

        center_col = tk.Frame(root, bg=BG_DARK)
        center_col.pack(side="left", fill="both", expand=True, padx=4, pady=4)

        right_col = tk.Frame(root, bg=BG_DARK, width=280)
        right_col.pack(side="right", fill="y", padx=(4, 6), pady=4)
        right_col.pack_propagate(False)

        # ── Left Column: Operations & Configuration
        tk.Label(left_col, text="[ PROCESS DISPATCHER ]", font=FONT_BODY,
                 bg=BG_DARK, fg=NEON_YELLOW).pack(pady=(4, 2))

        # Communication Mode Selector (Mailbox vs Direct)
        mode_box = tk.Frame(left_col, bg=BG_CARD, bd=1, relief="flat", padx=6, pady=4)
        mode_box.pack(fill="x", pady=4)
        tk.Label(mode_box, text="IPC Model:", font=FONT_SMALL, bg=BG_CARD, fg=TEXT_DIM).pack(anchor="w")
        self.ipc_mode_var = tk.StringVar(value="Mailbox (Indirect)")
        ipc_mode_menu = tk.OptionMenu(mode_box, self.ipc_mode_var,
                                      "Mailbox (Indirect)", "Direct Message Passing",
                                      command=self._on_ipc_mode_change)
        ipc_mode_menu.config(bg=BG_DARK, fg=NEON_BLUE, font=FONT_SMALL, bd=0, relief="flat")
        ipc_mode_menu["menu"].config(bg=BG_DARK, fg=NEON_BLUE, font=FONT_SMALL)
        ipc_mode_menu.pack(fill="x", pady=2)

        # Message Payload Input
        msg_box = tk.Frame(left_col, bg=BG_CARD, bd=1, relief="flat", padx=6, pady=4)
        msg_box.pack(fill="x", pady=4)
        tk.Label(msg_box, text="Message Payload:", font=FONT_SMALL, bg=BG_CARD, fg=TEXT_WHITE).pack(anchor="w")
        self.entry_msg = tk.Entry(msg_box, bg=BG_DARK, fg=NEON_YELLOW, font=FONT_BODY,
                                  insertbackground=NEON_YELLOW, relief="flat", bd=0,
                                  highlightthickness=1, highlightbackground=NEON_BLUE)
        self.entry_msg.insert(0, "Power Pellet")
        self.entry_msg.pack(fill="x", pady=2)

        # Quick Pellet Preset Buttons
        tk.Label(msg_box, text="Quick Presets:", font=FONT_SMALL, bg=BG_CARD, fg=TEXT_DIM).pack(anchor="w", pady=(2, 0))
        preset_grid = tk.Frame(msg_box, bg=BG_CARD)
        preset_grid.pack(fill="x", pady=2)
        for i, (name, val, icon) in enumerate(self.PELLET_PRESETS):
            btn = tk.Button(
                preset_grid, text=f"{icon} {name.split()[1]}",
                font=FONT_SMALL, bg=BG_DARK, fg=NEON_YELLOW,
                bd=0, relief="flat", cursor="hand2",
                command=lambda v=val: self._select_preset(v)
            )
            btn.grid(row=i // 2, column=i % 2, padx=2, pady=1, sticky="nsew")
        for col in range(2):
            preset_grid.columnconfigure(col, weight=1)

        # Target Ghost Receiver
        tk.Label(msg_box, text="Receiver Target:", font=FONT_SMALL, bg=BG_CARD, fg=TEXT_DIM).pack(anchor="w", pady=(4, 0))
        self.receiver_var = tk.StringVar(value="Blinky")
        rec_menu = tk.OptionMenu(msg_box, self.receiver_var,
                                 "Blinky", "Pinky", "Inky", "Clyde")
        rec_menu.config(bg=BG_DARK, fg=NEON_PINK, font=FONT_SMALL, bd=0, relief="flat")
        rec_menu["menu"].config(bg=BG_DARK, fg=NEON_PINK, font=FONT_SMALL)
        rec_menu.pack(fill="x", pady=2)

        # Manual Operations Buttons
        op_frame = tk.Frame(left_col, bg=BG_DARK)
        op_frame.pack(fill="x", pady=4)

        self.btn_send = neon_button(op_frame, "▶ SEND (PROC-A)", self.do_send, color=NEON_YELLOW, width=20)
        self.btn_send.pack(fill="x", pady=3)

        self.btn_recv = neon_button(op_frame, "◀ RECEIVE (PROC-B)", self.do_receive, color=NEON_BLUE, width=20)
        self.btn_recv.pack(fill="x", pady=3)

        self.btn_reset = neon_button(op_frame, "↺ RESET BUFFER", self.do_reset, color=NEON_PINK, width=20)
        self.btn_reset.pack(fill="x", pady=3)

        # Automated Simulation Controls (Producer-Consumer Generator)
        auto_frame = tk.Frame(left_col, bg=BG_CARD, bd=1, relief="flat", padx=6, pady=4)
        auto_frame.pack(fill="x", pady=4)
        tk.Label(auto_frame, text="[ AUTO PAC-PRODUCER ]", font=FONT_SMALL, bg=BG_CARD, fg=NEON_GREEN).pack(anchor="w")

        self.btn_auto_prod = tk.Button(
            auto_frame, text="⚡ AUTO-PRODUCE: OFF", font=FONT_SMALL,
            bg=BG_DARK, fg=TEXT_DIM, bd=1, relief="flat", cursor="hand2",
            command=self.toggle_auto_producer
        )
        self.btn_auto_prod.pack(fill="x", pady=2)

        self.prod_speed_var = tk.DoubleVar(value=1.5)
        tk.Scale(auto_frame, from_=0.3, to=3.0, resolution=0.1, orient="horizontal",
                 variable=self.prod_speed_var, label="Prod Interval (sec):",
                 bg=BG_CARD, fg=NEON_GREEN, troughcolor=BG_DARK, font=FONT_SMALL,
                 highlightthickness=0).pack(fill="x")

        self.btn_auto_cons = tk.Button(
            auto_frame, text="⚡ AUTO-CONSUME: OFF", font=FONT_SMALL,
            bg=BG_DARK, fg=TEXT_DIM, bd=1, relief="flat", cursor="hand2",
            command=self.toggle_auto_consumer
        )
        self.btn_auto_cons.pack(fill="x", pady=(6, 2))

        self.cons_speed_var = tk.DoubleVar(value=2.0)
        tk.Scale(auto_frame, from_=0.3, to=3.0, resolution=0.1, orient="horizontal",
                 variable=self.cons_speed_var, label="Cons Interval (sec):",
                 bg=BG_CARD, fg=NEON_BLUE, troughcolor=BG_DARK, font=FONT_SMALL,
                 highlightthickness=0).pack(fill="x")

        # Buffer Capacity Slider
        cap_frame = tk.Frame(left_col, bg=BG_CARD, bd=1, relief="flat", padx=6, pady=4)
        cap_frame.pack(fill="x", pady=4)
        self.cap_var = tk.IntVar(value=5)
        tk.Scale(cap_frame, from_=1, to=10, orient="horizontal",
                 variable=self.cap_var, command=self._on_capacity_slider,
                 label="Mailbox Slots (N):", bg=BG_CARD, fg=NEON_YELLOW,
                 troughcolor=BG_DARK, font=FONT_SMALL, highlightthickness=0).pack(fill="x")

        # ── Center Column: Pac-Man Arena Canvas + Pseudocode Tracer + Terminal Log
        self.canvas = tk.Canvas(center_col, bg=BG_DARK, bd=0, highlightthickness=2,
                                highlightbackground=NEON_BLUE, height=240)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Button-1>", self._on_canvas_click)

        # Pseudocode Step Tracer (Live Tanenbaum/Silberschatz Synchronizer)
        tracer_frame = tk.Frame(center_col, bg=BG_CARD, bd=1, relief="flat", pady=2)
        tracer_frame.pack(fill="x", pady=(4, 2))

        tracer_hdr = tk.Frame(tracer_frame, bg=BG_CARD)
        tracer_hdr.pack(fill="x", padx=6)
        tk.Label(tracer_hdr, text="[ SYNCHRONIZATION ALGORITHM TRACER (SEMAPHORES) ]",
                 font=FONT_SMALL, bg=BG_CARD, fg=NEON_YELLOW).pack(side="left")

        tracer_grid = tk.Frame(tracer_frame, bg=BG_CARD)
        tracer_grid.pack(fill="x", padx=6, pady=2)

        # Producer pseudocode lines
        self.prod_code_lines = []
        prod_box = tk.Frame(tracer_grid, bg=BG_DARK, padx=4, pady=2)
        prod_box.pack(side="left", fill="both", expand=True, padx=(0, 2))
        tk.Label(prod_box, text="Producer (Pac-Man):", font=FONT_SMALL, bg=BG_DARK, fg=NEON_YELLOW).pack(anchor="w")
        p_texts = [
            "1: wait(empty);  // Decrement empty slots",
            "2: wait(mutex);  // Enter Critical Section",
            "3: buffer.put(packet);",
            "4: signal(mutex);// Exit Critical Section",
            "5: signal(full); // Signal waiting consumer",
        ]
        for t in p_texts:
            lbl = tk.Label(prod_box, text=t, font=FONT_CODE, bg=BG_DARK, fg=TEXT_DIM, anchor="w")
            lbl.pack(fill="x")
            self.prod_code_lines.append(lbl)

        # Consumer pseudocode lines
        self.cons_code_lines = []
        cons_box = tk.Frame(tracer_grid, bg=BG_DARK, padx=4, pady=2)
        cons_box.pack(side="right", fill="both", expand=True, padx=(2, 0))
        tk.Label(cons_box, text="Consumer (Ghost):", font=FONT_SMALL, bg=BG_DARK, fg=NEON_BLUE).pack(anchor="w")
        c_texts = [
            "1: wait(full);   // Wait if buffer empty",
            "2: wait(mutex);  // Enter Critical Section",
            "3: packet = buffer.get();",
            "4: signal(mutex);// Exit Critical Section",
            "5: signal(empty);// Signal waiting producer",
        ]
        for t in c_texts:
            lbl = tk.Label(cons_box, text=t, font=FONT_CODE, bg=BG_DARK, fg=TEXT_DIM, anchor="w")
            lbl.pack(fill="x")
            self.cons_code_lines.append(lbl)

        # Terminal Activity Log
        log_frame = tk.Frame(center_col, bg=BG_PANEL)
        log_frame.pack(fill="x", pady=(2, 0))
        log_hdr = tk.Frame(log_frame, bg=BG_PANEL)
        log_hdr.pack(fill="x", padx=4)
        tk.Label(log_hdr, text="[ IPC TRANSACTION KERNEL LOG ]", font=FONT_SMALL,
                 bg=BG_PANEL, fg=TEXT_DIM).pack(side="left")
        self.log_sf = scrolled_text(log_frame, height=5, width=70)
        self.log_sf.pack(fill="x", padx=2, pady=2)
        self.log_txt = self.log_sf.txt

        # ── Right Column: Semaphores Meter & Message Inspector
        tk.Label(right_col, text="[ OS SEMAPHORE CONTROLS ]", font=FONT_BODY,
                 bg=BG_DARK, fg=NEON_GREEN).pack(pady=(4, 2))

        # 3 Real-time Semaphore Meters
        sem_panel = tk.Frame(right_col, bg=BG_CARD, bd=1, relief="flat", padx=8, pady=6)
        sem_panel.pack(fill="x", pady=4)

        # Mutex Semaphore Display
        m_row = tk.Frame(sem_panel, bg=BG_CARD)
        m_row.pack(fill="x", pady=3)
        tk.Label(m_row, text="MUTEX (Binary):", font=FONT_SMALL, bg=BG_CARD, fg=TEXT_WHITE).pack(side="left")
        self.badge_mutex = tk.Label(m_row, text="1 [FREE]", font=FONT_SMALL, bg=NEON_GREEN, fg=BG_DARK, width=10)
        self.badge_mutex.pack(side="right")

        # Empty Counting Semaphore
        e_row = tk.Frame(sem_panel, bg=BG_CARD)
        e_row.pack(fill="x", pady=3)
        tk.Label(e_row, text="EMPTY (Counting):", font=FONT_SMALL, bg=BG_CARD, fg=TEXT_WHITE).pack(side="left")
        self.badge_empty = tk.Label(e_row, text="5", font=FONT_SMALL, bg=NEON_BLUE, fg=BG_DARK, width=10)
        self.badge_empty.pack(side="right")

        # Full Counting Semaphore
        f_row = tk.Frame(sem_panel, bg=BG_CARD)
        f_row.pack(fill="x", pady=3)
        tk.Label(f_row, text="FULL (Counting):", font=FONT_SMALL, bg=BG_CARD, fg=TEXT_WHITE).pack(side="left")
        self.badge_full = tk.Label(f_row, text="0", font=FONT_SMALL, bg=NEON_PURPLE, fg=BG_DARK, width=10)
        self.badge_full.pack(side="right")

        # Process States Display
        proc_panel = tk.Frame(right_col, bg=BG_CARD, bd=1, relief="flat", padx=8, pady=6)
        proc_panel.pack(fill="x", pady=4)
        tk.Label(proc_panel, text="[ PROCESS RUNTIME STATES ]", font=FONT_SMALL, bg=BG_CARD, fg=TEXT_DIM).pack(anchor="w")

        p_row = tk.Frame(proc_panel, bg=BG_CARD)
        p_row.pack(fill="x", pady=2)
        tk.Label(p_row, text="PROC-A (Pac-Man):", font=FONT_SMALL, bg=BG_CARD, fg=NEON_YELLOW).pack(side="left")
        self.badge_proc_a = tk.Label(p_row, text="RUNNING", font=FONT_SMALL, bg=NEON_GREEN, fg=BG_DARK, width=10)
        self.badge_proc_a.pack(side="right")

        g_row = tk.Frame(proc_panel, bg=BG_CARD)
        g_row.pack(fill="x", pady=2)
        tk.Label(g_row, text="PROC-B (Ghost):", font=FONT_SMALL, bg=BG_CARD, fg=NEON_PINK).pack(side="left")
        self.badge_proc_b = tk.Label(g_row, text="RUNNING", font=FONT_SMALL, bg=NEON_GREEN, fg=BG_DARK, width=10)
        self.badge_proc_b.pack(side="right")

        # Message Packet Inspector (Shows on click or latest)
        tk.Label(right_col, text="[ PACKET INSPECTOR ]", font=FONT_BODY,
                 bg=BG_DARK, fg=NEON_BLUE).pack(pady=(6, 2))
        self.insp_frame = tk.Frame(right_col, bg=BG_CARD, bd=1, relief="flat", padx=8, pady=6)
        self.insp_frame.pack(fill="both", expand=True, pady=2)

        self.lbl_insp_id = tk.Label(self.insp_frame, text="ID: None (Queue empty)", font=FONT_SMALL, bg=BG_CARD, fg=NEON_YELLOW, anchor="w")
        self.lbl_insp_id.pack(fill="x")
        self.lbl_insp_sender = tk.Label(self.insp_frame, text="Sender: -", font=FONT_SMALL, bg=BG_CARD, fg=TEXT_WHITE, anchor="w")
        self.lbl_insp_sender.pack(fill="x")
        self.lbl_insp_recv = tk.Label(self.insp_frame, text="Receiver: -", font=FONT_SMALL, bg=BG_CARD, fg=TEXT_WHITE, anchor="w")
        self.lbl_insp_recv.pack(fill="x")
        self.lbl_insp_time = tk.Label(self.insp_frame, text="Timestamp: -", font=FONT_SMALL, bg=BG_CARD, fg=TEXT_DIM, anchor="w")
        self.lbl_insp_time.pack(fill="x")
        self.lbl_insp_payload = tk.Label(self.insp_frame, text="Payload: -", font=FONT_SMALL, bg=BG_CARD, fg=NEON_GREEN, anchor="w")
        self.lbl_insp_payload.pack(fill="x")
        self.lbl_insp_size = tk.Label(self.insp_frame, text="Packet Size: -", font=FONT_SMALL, bg=BG_CARD, fg=TEXT_DIM, anchor="w")
        self.lbl_insp_size.pack(fill="x")

        # Instruction Tip
        tk.Label(self.insp_frame, text="\nTip: Click any mailbox slot\non the canvas to inspect its\nfull IPC packet envelope!",
                 font=FONT_SMALL, bg=BG_CARD, fg=TEXT_DIM, justify="left").pack(fill="x")

    def _select_preset(self, val: str):
        self.entry_msg.delete(0, "end")
        self.entry_msg.insert(0, val)

    def _on_ipc_mode_change(self, choice: str):
        self._log(f"⚙ IPC Mode switched to: {choice}")

    def _on_capacity_slider(self, val):
        try:
            new_c = int(val)
            self.buffer.resize(new_c)
            self._log(f"⚙ Mailbox buffer resized to {new_c} slots (empty_sem={self.buffer.empty_sem}, full_sem={self.buffer.full_sem})")
            self._update_semaphores_ui()
        except ValueError:
            pass

    # ═════════════════════════════════════════════════════════════════════════
    # SUB-TAB 2: CHALLENGE MISSIONS (GAME LEARNING)
    # ═════════════════════════════════════════════════════════════════════════
    def _build_missions_view(self):
        root = self.frame_missions

        hdr = tk.Frame(root, bg=BG_PANEL, pady=8)
        hdr.pack(fill="x")
        tk.Label(hdr, text="PAC-MAN IPC ACADEMY: MISSION CHALLENGES",
                 font=FONT_HEADER, bg=BG_PANEL, fg=NEON_YELLOW).pack()
        tk.Label(hdr, text="Complete these interactive synchronization scenarios to master OS concepts!",
                 font=FONT_SMALL, bg=BG_PANEL, fg=TEXT_DIM).pack()

        # Score display
        self.lbl_mission_score = tk.Label(root, text="ARCADE SCORE: 000000 | RANK: NOVICE KERNEL",
                                          font=FONT_SUBHEADER, bg=BG_DARK, fg=NEON_GREEN)
        self.lbl_mission_score.pack(pady=8)

        # 4 Mission Cards in a 2x2 grid
        grid = tk.Frame(root, bg=BG_DARK)
        grid.pack(fill="both", expand=True, padx=20, pady=10)

        self.mission_cards = []
        missions = [
            ("MISSION 1: THE FIRST HANDSHAKE",
             "Demonstrate message passing by successfully dispatching 3 messages\nfrom Pac-Man (PROC-A) to the Ghost mailbox.",
             "Target: Send 3 packets", "m1"),
            ("MISSION 2: THE BOUNDED OVERFLOW TEST",
             "Demonstrate backpressure & bounded-buffer overflow by filling all slots.\nWitness Pac-Man entering the BLOCKED state on wait(empty)!",
             "Target: Fill Buffer to 100% capacity", "m2"),
            ("MISSION 3: GHOST STARVATION RESCUE",
             "Drain all messages from the buffer until the Ghost is BLOCKED on wait(full).\nThen dispatch a new pellet to rescue the consumer!",
             "Target: Trigger Empty Block then unblock", "m3"),
            ("MISSION 4: DYNAMIC RATE BALANCING",
             "Turn ON both Auto-Produce and Auto-Consume. Adjust their sliders\nto maintain buffer occupancy between 30% and 70% for 5 seconds!",
             "Target: Balance buffer for 5s", "m4")
        ]

        for idx, (title, desc, target, key) in enumerate(missions):
            row = idx // 2
            col = idx % 2
            c_frame = tk.Frame(grid, bg=BG_CARD, bd=2, relief="flat",
                               highlightthickness=1, highlightbackground=NEON_BLUE, padx=12, pady=10)
            c_frame.grid(row=row, column=col, padx=12, pady=8, sticky="nsew")

            tk.Label(c_frame, text=title, font=FONT_BODY, bg=BG_CARD, fg=NEON_YELLOW).pack(anchor="w")
            tk.Label(c_frame, text=desc, font=FONT_SMALL, bg=BG_CARD, fg=TEXT_WHITE, justify="left").pack(anchor="w", pady=4)

            p_lbl = tk.Label(c_frame, text=f"Status: INCOMPLETE ❌", font=FONT_SMALL, bg=BG_CARD, fg=NEON_RED)
            p_lbl.pack(anchor="w", pady=2)

            btn = neon_button(c_frame, "▶ JUMP TO ARENA",
                              lambda: self._switch_sub_tab("arena"), color=NEON_BLUE, width=16)
            btn.pack(anchor="e", pady=4)

            self.mission_cards.append((key, p_lbl, c_frame))

        for c in range(2):
            grid.columnconfigure(c, weight=1)
        for r in range(2):
            grid.rowconfigure(r, weight=1)

    def _update_mission_ui(self):
        # Mission 1 check
        m1_done = self.mission_flags["m1_sent"] >= 3
        # Mission 2 check
        m2_done = self.mission_flags["m2_full_hit"]
        # Mission 3 check
        m3_done = self.mission_flags["m3_empty_hit"]
        # Mission 4 check
        m4_done = self.mission_flags["m4_balanced_ticks"] >= 50

        statuses = [m1_done, m2_done, m3_done, m4_done]
        completed = sum(statuses)
        self.mission_scores = completed * 2500

        ranks = ["NOVICE KERNEL", "APPRENTICE HACKER", "SYSTEM ENGINEER", "OS ARCHITECT", "MASTER OF KERNEL"]
        self.lbl_mission_score.config(
            text=f"ARCADE SCORE: {self.mission_scores:06d} | RANK: {ranks[completed]}"
        )

        for (key, lbl, card), is_done in zip(self.mission_cards, statuses):
            if is_done:
                lbl.config(text="Status: COMPLETED! ⭐", fg=NEON_GREEN)
                card.config(highlightbackground=NEON_GREEN)
            else:
                lbl.config(text="Status: INCOMPLETE ❌", fg=NEON_RED)
                card.config(highlightbackground=NEON_BLUE)

    # ═════════════════════════════════════════════════════════════════════════
    # SUB-TAB 3: ARCADE QUIZ BATTLE
    # ═════════════════════════════════════════════════════════════════════════
    def _build_quiz_view(self):
        root = self.frame_quiz

        hdr = tk.Frame(root, bg=BG_PANEL, pady=8)
        hdr.pack(fill="x")
        tk.Label(hdr, text="PAC-MAN OS QUIZ: INTERPROCESS COMMUNICATION",
                 font=FONT_HEADER, bg=BG_PANEL, fg=NEON_YELLOW).pack()
        tk.Label(hdr, text="Answer OS IPC questions to help Pac-Man chomp the synchronization dots!",
                 font=FONT_SMALL, bg=BG_PANEL, fg=TEXT_DIM).pack()

        # Quiz progress canvas (Pac-Man moving across dots)
        self.quiz_canvas = tk.Canvas(root, bg=BG_CARD, height=70, highlightthickness=1,
                                     highlightbackground=NEON_BLUE)
        self.quiz_canvas.pack(fill="x", padx=40, pady=8)

        # Question Container Card
        self.q_card = tk.Frame(root, bg=BG_CARD, bd=2, relief="flat",
                               highlightthickness=1, highlightbackground=NEON_YELLOW, padx=20, pady=14)
        self.q_card.pack(fill="both", expand=True, padx=40, pady=8)

        self.lbl_q_title = tk.Label(self.q_card, text="QUESTION 1 OF 5", font=FONT_HEADER, bg=BG_CARD, fg=NEON_YELLOW)
        self.lbl_q_title.pack(anchor="w")

        self.lbl_q_text = tk.Label(self.q_card, text="", font=FONT_BODY, bg=BG_CARD, fg=TEXT_WHITE, justify="left", wraplength=700)
        self.lbl_q_text.pack(anchor="w", pady=(8, 14))

        self.q_opt_buttons = []
        for i in range(4):
            btn = tk.Button(
                self.q_card, text="", font=FONT_BODY, bg=BG_DARK, fg=TEXT_WHITE,
                activebackground=NEON_YELLOW, activeforeground=BG_DARK,
                bd=1, relief="flat", highlightthickness=1, highlightbackground=TEXT_DIM,
                anchor="w", padx=12, pady=6, cursor="hand2",
                command=lambda idx=i: self._on_quiz_answer(idx)
            )
            btn.pack(fill="x", pady=3)
            self.q_opt_buttons.append(btn)

        self.lbl_q_feedback = tk.Label(self.q_card, text="", font=FONT_BODY, bg=BG_CARD, fg=NEON_GREEN, justify="left")
        self.lbl_q_feedback.pack(anchor="w", pady=8)

        self.btn_next_q = neon_button(self.q_card, "NEXT QUESTION ▶", self._next_quiz_question, color=NEON_GREEN, width=18)
        self.btn_next_q.pack(anchor="e")
        self.btn_next_q.pack_forget()

        # Quiz bank
        self.quiz_bank = [
            {
                "q": "What is the primary function of a Bounded Buffer in Interprocess Communication (IPC)?",
                "options": [
                    "A. To eliminate the need for CPU context switching completely.",
                    "B. To provide a fixed-capacity temporary storage decoupling asynchronous sender and receiver.",
                    "C. To prevent the operating system from allocating virtual memory.",
                    "D. To encrypt all messages with public key cryptography."
                ],
                "answer": 1,
                "explain": "Correct! A bounded buffer decouples producer and consumer processes so they can execute at independent speeds without losing data."
            },
            {
                "q": "In classic Dijkstra Bounded-Buffer synchronization, what does the 'empty' semaphore track?",
                "options": [
                    "A. The number of vacant slots available in the buffer for the producer to write into.",
                    "B. The number of blocked consumer processes.",
                    "C. A binary flag indicating whether the entire system is halted.",
                    "D. The number of CPU cores idle."
                ],
                "answer": 0,
                "explain": "Correct! The 'empty' counting semaphore starts at N (buffer capacity) and decrements when the producer enqueues, blocking the producer when 0."
            },
            {
                "q": "What happens if a process attempts to receive from an EMPTY message mailbox in blocking IPC?",
                "options": [
                    "A. The operating system crashes with a kernel panic.",
                    "B. The process is placed into the BLOCKED/WAITING state until a message arrives.",
                    "C. The process overwrites the producer's program counter.",
                    "D. The receiver receives random garbage bytes immediately."
                ],
                "answer": 1,
                "explain": "Correct! In blocking (synchronous) receive, the consumer blocks on wait(full) until the producer deposits a message and calls signal(full)."
            },
            {
                "q": "Why is a 'mutex' (mutual exclusion) semaphore necessary even when counting semaphores are present?",
                "options": [
                    "A. It makes the simulation run 2x faster.",
                    "B. It prevents race conditions and data corruption when modifying queue pointers (head/tail).",
                    "C. It is only required for graphics rendering.",
                    "D. Mutex semaphores are never used with counting semaphores."
                ],
                "answer": 1,
                "explain": "Correct! Counting semaphores track resource availability, but a binary mutex is essential to ensure only ONE process updates the buffer pointers at a time."
            },
            {
                "q": "Which IPC model allows processes to communicate indirectly without knowing each other's Process ID (PID)?",
                "options": [
                    "A. Direct Symmetric Communication",
                    "B. Direct Asymmetric Communication",
                    "C. Mailbox / Port-based Indirect Communication",
                    "D. Polling CPU registers directly"
                ],
                "answer": 2,
                "explain": "Correct! Mailbox/port-based IPC decouples sender and receiver addresses; any authorized process can send to or read from the shared mailbox."
            }
        ]

    def _render_quiz_question(self):
        self.quiz_answered = False
        self.btn_next_q.pack_forget()
        self.lbl_q_feedback.config(text="")

        if self.quiz_index >= len(self.quiz_bank):
            # Quiz complete
            self.lbl_q_title.config(text="🎉 QUIZ COMPLETE!")
            score_pct = (self.quiz_score / len(self.quiz_bank)) * 100
            grade = "A+ (KERNEL ARCHITECT)" if score_pct == 100 else ("B (KERNEL HACKER)" if score_pct >= 60 else "C (CADET)")
            self.lbl_q_text.config(
                text=f"Your Final Score: {self.quiz_score} / {len(self.quiz_bank)} ({score_pct:.0f}%)\n"
                     f"Certification Grade: {grade}\n\n"
                     f"You have demonstrated outstanding mastery of OS IPC & Process Synchronization!"
            )
            for btn in self.q_opt_buttons:
                btn.pack_forget()
            self.btn_next_q.config(text="↺ RETAKE QUIZ", command=self._restart_quiz)
            self.btn_next_q.pack(anchor="e")
            self._draw_quiz_track()
            return

        item = self.quiz_bank[self.quiz_index]
        self.lbl_q_title.config(text=f"QUESTION {self.quiz_index + 1} OF {len(self.quiz_bank)} (SCORE: {self.quiz_score})")
        self.lbl_q_text.config(text=item["q"])

        for i, opt in enumerate(item["options"]):
            btn = self.q_opt_buttons[i]
            btn.pack(fill="x", pady=3)
            btn.config(text=opt, bg=BG_DARK, fg=TEXT_WHITE, highlightbackground=TEXT_DIM)

        self._draw_quiz_track()

    def _draw_quiz_track(self):
        c = self.quiz_canvas
        c.delete("all")
        w = c.winfo_width() if c.winfo_width() > 10 else 700
        h = 70
        total_q = len(self.quiz_bank)
        step_w = (w - 100) / max(1, total_q)

        # Draw dots
        for i in range(total_q):
            cx = 50 + i * step_w
            cy = h // 2
            if i < self.quiz_index:
                # Eaten dot (empty ring)
                c.create_oval(cx - 3, cy - 3, cx + 3, cy + 3, fill="", outline=TEXT_DIM)
            else:
                # Active power pellet
                c.create_oval(cx - 6, cy - 6, cx + 6, cy + 6, fill=NEON_YELLOW, outline=NEON_ORANGE)
                c.create_text(cx, cy + 18, text=f"Q{i+1}", font=FONT_SMALL, fill=TEXT_DIM)

        # Draw Fruit Bonus at the end
        fx = 50 + total_q * step_w
        c.create_text(fx, h // 2, text="🍒", font=("Segoe UI Emoji", 16))

        # Draw Pac-Man at current question index
        pac_x = 50 + self.quiz_index * step_w
        draw_pacman(c, pac_x, h // 2, r=18, mouth_angle=35, color=NEON_YELLOW, tag="quiz_pac")

    def _on_quiz_answer(self, chosen_idx: int):
        if self.quiz_answered:
            return
        self.quiz_answered = True
        item = self.quiz_bank[self.quiz_index]

        if chosen_idx == item["answer"]:
            self.quiz_score += 1
            SOUND_ENGINE.play_success()
            self.q_opt_buttons[chosen_idx].config(bg="#004D20", fg=NEON_GREEN, highlightbackground=NEON_GREEN)
            self.lbl_q_feedback.config(text=f"✔ CORRECT! {item['explain']}", fg=NEON_GREEN)
        else:
            SOUND_ENGINE.play_quiz_wrong()
            self.q_opt_buttons[chosen_idx].config(bg="#4D0010", fg=NEON_RED, highlightbackground=NEON_RED)
            correct_idx = item["answer"]
            self.q_opt_buttons[correct_idx].config(bg="#004D20", fg=NEON_GREEN, highlightbackground=NEON_GREEN)
            self.lbl_q_feedback.config(text=f"✘ INCORRECT. {item['explain']}", fg=NEON_RED)

        self.btn_next_q.config(text="CONTINUE ▶", command=self._next_quiz_question)
        self.btn_next_q.pack(anchor="e", pady=6)

    def _next_quiz_question(self):
        self.quiz_index += 1
        self._render_quiz_question()

    def _restart_quiz(self):
        self.quiz_index = 0
        self.quiz_score = 0
        self._render_quiz_question()

    # ═════════════════════════════════════════════════════════════════════════
    # SUB-TAB 4: EDUCATIONAL CONCEPT GUIDE
    # ═════════════════════════════════════════════════════════════════════════
    def _build_guide_view(self):
        root = self.frame_guide

        hdr = tk.Frame(root, bg=BG_PANEL, pady=6)
        hdr.pack(fill="x")
        tk.Label(hdr, text="OPERATING SYSTEMS IPC & SYNCHRONIZATION REFERENCE GUIDE",
                 font=FONT_HEADER, bg=BG_PANEL, fg=NEON_YELLOW).pack()

        sf = scrolled_text(root, height=22, width=90)
        sf.pack(fill="both", expand=True, padx=20, pady=10)
        txt = sf.txt

        guide_content = """
================================================================================
              OPERATING SYSTEMS CONCEPT GUIDE: IPC & SYNCHRONIZATION
================================================================================

1. WHAT IS INTERPROCESS COMMUNICATION (IPC)?
--------------------------------------------------------------------------------
In modern operating systems, processes execute in isolated address spaces to
prevent accidental or malicious corruption. When multiple processes must
collaborate to complete a task, they require Interprocess Communication (IPC).

IPC models fall into two primary categories:
  A. Shared Memory:
     - Processes map a common region of physical memory into their address spaces.
     - Maximum speed, but requires explicit programmer synchronization to prevent
       race conditions.
  B. Message Passing:
     - The OS kernel provides communication primitives: send() and receive().
     - Processes exchange formatted packets through channels, mailboxes, or pipes.
     - Inherently handles distributed systems and multi-core architectures safely.

2. DIRECT VS. INDIRECT (MAILBOX) COMMUNICATION
--------------------------------------------------------------------------------
- Direct Communication:
  Processes explicitly name the recipient:
      send(Process_B, message);
      receive(Process_A, message);
  Tight coupling: altering process identifiers requires modifying communication code.

- Indirect (Mailbox / Port) Communication:
  Messages are sent to and received from shared mailboxes or ports:
      send(Mailbox_1, message);
      receive(Mailbox_1, message);
  Benefits: Many-to-many communication, decoupling of process lifecycles.

3. THE BOUNDED-BUFFER (PRODUCER-CONSUMER) PROBLEM
--------------------------------------------------------------------------------
The bounded-buffer is the canonical paradigm for cooperating processes:
  - Producer Process (Pac-Man): Generates information and places it into a buffer of size N.
  - Consumer Process (Ghost): Consumes information by removing it from the buffer.

The fundamental constraints:
  - Bounded Capacity: The buffer holds at most N items.
  - Backpressure (Buffer Full): If the buffer is full, the producer MUST be suspended (blocked)
    until a slot is freed by the consumer.
  - Starvation (Buffer Empty): If the buffer is empty, the consumer MUST be suspended (blocked)
    until an item is deposited by the producer.

4. SYNCHRONIZATION WITH THREE SEMAPHORES (DIJKSTRA'S ALGORITHM)
--------------------------------------------------------------------------------
To coordinate without race conditions, three semaphores are deployed:

  1. mutex (Binary Semaphore, initialized to 1):
     Guarantees Mutual Exclusion so only one process modifies buffer pointers at once.

  2. empty (Counting Semaphore, initialized to N):
     Counts available empty slots. Producer decrements (wait); consumer increments (signal).

  3. full (Counting Semaphore, initialized to 0):
     Counts occupied slots. Producer increments (signal); consumer decrements (wait).

Pseudocode:
  Producer:
      item = produce_item();
      wait(empty);    // Decrement empty slots; BLOCKS if empty == 0
      wait(mutex);    // Acquire buffer lock
      buffer.append(item);
      signal(mutex);  // Release buffer lock
      signal(full);   // Increment full slots; WAKES blocked consumer

  Consumer:
      wait(full);     // Decrement full slots; BLOCKS if full == 0
      wait(mutex);    // Acquire buffer lock
      item = buffer.remove();
      signal(mutex);  // Release buffer lock
      signal(empty);  // Increment empty slots; WAKES blocked producer
      consume_item(item);

5. REAL-WORLD OPERATING SYSTEM ANALOGS
--------------------------------------------------------------------------------
- UNIX / Linux:
  * Pipes (`pipe()`, `mkfifo`): Bounded circular buffers in kernel memory.
  * POSIX Message Queues (`mq_open`, `mq_send`, `mq_receive`): Priority queues.
  * Sockets (`socket()`, `bind()`, `connect()`): IPC across networks and domains.
- Microsoft Windows:
  * MailSlots: One-way broadcast IPC.
  * Named Pipes: Two-way buffered IPC with security descriptors.
  * ALPC (Advanced Local Procedure Calls): High-speed kernel message passing.

================================================================================
"""
        txt.configure(state="normal")
        txt.delete("1.0", "end")
        txt.insert("end", guide_content)
        txt.configure(state="disabled")

    # ═════════════════════════════════════════════════════════════════════════
    # ARENA OPERATIONS & SYNCHRONIZATION LOGIC
    # ═════════════════════════════════════════════════════════════════════════
    def do_send(self):
        """Execute a single producer send operation."""
        payload = self.entry_msg.get().strip()
        if not payload:
            self._log("⚠ Send Error: Message payload cannot be empty!")
            SOUND_ENGINE.play_blocked()
            return

        target_ghost = self.receiver_var.get()
        # Find icon
        icon = "🟡"
        for _, name, ic in self.PELLET_PRESETS:
            if name.lower() in payload.lower():
                icon = ic
                break

        packet = MessagePacket(
            msg_id=self.msg_counter,
            sender="Pac-Man [PID: 101]",
            receiver=f"{target_ghost} [PID: 202]",
            msg_type="Arcade Pellet",
            payload=payload,
            icon=icon
        )

        # Highlight Step 1 & 2 in Tracer
        self._highlight_tracer_prod(0)  # wait(empty)

        ok, reason = self.buffer.enqueue(packet)
        if ok:
            self.msg_counter += 1
            self.sent_count += 1
            self.proc_a_state = ProcessState.SENDING
            SOUND_ENGINE.play_send()

            # Launch traveling pellet animation
            self._pellets_traveling.append({
                "type": "send",
                "progress": 0.0,
                "packet": packet,
                "icon": icon
            })

            # Highlight success lines in tracer
            self._highlight_tracer_prod(2)  # put
            self._safe_after(300, lambda: self._highlight_tracer_prod(4))  # signal(full)
            self._safe_after(600, lambda: self._clear_tracer_prod())

            self._log(f"PROC-A (Pac-Man) → Enqueued {icon} #{packet.msg_id} \"{payload}\" to Mailbox")
            self._inspect_packet(packet)

            # Update mission flags
            self.mission_flags["m1_sent"] += 1

            # Restore PROC-B if it was blocked on empty
            if self.proc_b_state == ProcessState.BLOCKED:
                self.proc_b_state = ProcessState.RUNNING
                self._log("✔ Consumer (PROC-B) unblocked by incoming message signal(full)!")
                if self.mission_flags["m3_empty_hit"]:
                    self._update_mission_ui()

        else:
            # Buffer FULL! Producer is BLOCKED!
            self.proc_a_state = ProcessState.BLOCKED
            SOUND_ENGINE.play_blocked()
            self._highlight_tracer_prod(0, blocked=True)
            self._log(f"⚠ BUFFER OVERFLOW BLOCKED: PROC-A suspended on wait(empty). Buffer is FULL ({self.buffer.count}/{self.buffer.capacity})")
            self.mission_flags["m2_full_hit"] = True
            self._update_mission_ui()

        self._update_semaphores_ui()

    def do_receive(self):
        """Execute a single consumer receive operation."""
        # Highlight Step 1 in Tracer
        self._highlight_tracer_cons(0)  # wait(full)

        packet, reason = self.buffer.dequeue()
        if packet is not None:
            self.recv_count += 1
            self.proc_b_state = ProcessState.RECEIVING
            SOUND_ENGINE.play_receive()

            # Launch traveling pellet animation from buffer to ghost
            self._pellets_traveling.append({
                "type": "recv",
                "progress": 0.0,
                "packet": packet,
                "icon": packet.icon
            })

            # Highlight success lines in tracer
            self._highlight_tracer_cons(2)  # get
            self._safe_after(300, lambda: self._highlight_tracer_cons(4))  # signal(empty)
            self._safe_after(600, lambda: self._clear_tracer_cons())

            self._log(f"PROC-B ({packet.receiver.split()[0]}) ← Dequeued {packet.icon} #{packet.msg_id} \"{packet.payload}\" from Mailbox")
            self._inspect_packet(packet)

            # Restore PROC-A if it was blocked on full
            if self.proc_a_state == ProcessState.BLOCKED:
                self.proc_a_state = ProcessState.RUNNING
                self._log("✔ Producer (PROC-A) unblocked by freed slot signal(empty)!")

        else:
            # Buffer EMPTY! Consumer is BLOCKED!
            self.proc_b_state = ProcessState.BLOCKED
            SOUND_ENGINE.play_blocked()
            self._highlight_tracer_cons(0, blocked=True)
            self._log(f"⚠ BUFFER STARVATION BLOCKED: PROC-B suspended on wait(full). Buffer is EMPTY (0/{self.buffer.capacity})")
            self.mission_flags["m3_empty_hit"] = True
            self._update_mission_ui()

        self._update_semaphores_ui()

    def do_reset(self):
        """Reset the buffer and process states to clean initial state."""
        self.buffer.clear()
        self.proc_a_state = ProcessState.RUNNING
        self.proc_b_state = ProcessState.RUNNING
        self._pellets_traveling.clear()
        self._clear_tracer_prod()
        self._clear_tracer_cons()
        self._update_semaphores_ui()
        SOUND_ENGINE.play_success()
        self._log("↺ System Reset: Mailbox cleared, semaphores reset (mutex=1, empty=N, full=0), processes RUNNING.")

    # ── Auto-Run Generators ──────────────────────────────────────────────────
    def toggle_auto_producer(self):
        self.auto_producer_active = not self.auto_producer_active
        if self.auto_producer_active:
            self.btn_auto_prod.config(text="⚡ AUTO-PRODUCE: ON", bg="#004D20", fg=NEON_GREEN)
            self._run_auto_producer_loop()
        else:
            self.btn_auto_prod.config(text="⚡ AUTO-PRODUCE: OFF", bg=BG_DARK, fg=TEXT_DIM)
            if self._auto_prod_after_id:
                self.after_cancel(self._auto_prod_after_id)
                self._auto_prod_after_id = None

    def _run_auto_producer_loop(self):
        if not self.auto_producer_active:
            return
        # Pick random preset
        name, val, ic = random.choice(self.PELLET_PRESETS)
        self.entry_msg.delete(0, "end")
        self.entry_msg.insert(0, val)
        self.do_send()
        interval_ms = int(self.prod_speed_var.get() * 1000)
        self._auto_prod_after_id = self.after(interval_ms, self._run_auto_producer_loop)

    def toggle_auto_consumer(self):
        self.auto_consumer_active = not self.auto_consumer_active
        if self.auto_consumer_active:
            self.btn_auto_cons.config(text="⚡ AUTO-CONSUME: ON", bg="#002D4D", fg=NEON_BLUE)
            self._run_auto_consumer_loop()
        else:
            self.btn_auto_cons.config(text="⚡ AUTO-CONSUME: OFF", bg=BG_DARK, fg=TEXT_DIM)
            if self._auto_cons_after_id:
                self.after_cancel(self._auto_cons_after_id)
                self._auto_cons_after_id = None

    def _run_auto_consumer_loop(self):
        if not self.auto_consumer_active:
            return
        self.do_receive()
        interval_ms = int(self.cons_speed_var.get() * 1000)
        self._auto_cons_after_id = self.after(interval_ms, self._run_auto_consumer_loop)

    # ── Tracer & UI Highlights ───────────────────────────────────────────────
    def _highlight_tracer_prod(self, idx: int, blocked: bool = False):
        for i, lbl in enumerate(self.prod_code_lines):
            if i == idx:
                bg_col = "#660010" if blocked else "#554400"
                fg_col = NEON_RED if blocked else NEON_YELLOW
                lbl.config(bg=bg_col, fg=fg_col)
            else:
                lbl.config(bg=BG_DARK, fg=TEXT_DIM)

    def _clear_tracer_prod(self):
        for lbl in self.prod_code_lines:
            lbl.config(bg=BG_DARK, fg=TEXT_DIM)

    def _highlight_tracer_cons(self, idx: int, blocked: bool = False):
        for i, lbl in enumerate(self.cons_code_lines):
            if i == idx:
                bg_col = "#660010" if blocked else "#003366"
                fg_col = NEON_RED if blocked else NEON_BLUE
                lbl.config(bg=bg_col, fg=fg_col)
            else:
                lbl.config(bg=BG_DARK, fg=TEXT_DIM)

    def _clear_tracer_cons(self):
        for lbl in self.cons_code_lines:
            lbl.config(bg=BG_DARK, fg=TEXT_DIM)

    def _update_semaphores_ui(self):
        # Mutex badge
        m_val = self.buffer.mutex
        if m_val == 1:
            self.badge_mutex.config(text="1 [FREE]", bg=NEON_GREEN, fg=BG_DARK)
        else:
            self.badge_mutex.config(text="0 [LOCKED]", bg=NEON_RED, fg=TEXT_WHITE)

        # Counting semaphores
        self.badge_empty.config(text=str(self.buffer.empty_sem))
        self.badge_full.config(text=str(self.buffer.full_sem))

        # Process Badges
        p_colors = {
            ProcessState.RUNNING: (NEON_GREEN, BG_DARK),
            ProcessState.SENDING: (NEON_YELLOW, BG_DARK),
            ProcessState.RECEIVING: (NEON_BLUE, BG_DARK),
            ProcessState.BLOCKED: (NEON_RED, TEXT_WHITE),
            ProcessState.WAITING: (NEON_ORANGE, BG_DARK),
        }
        ab, af = p_colors.get(self.proc_a_state, (NEON_GREEN, BG_DARK))
        bb, bf = p_colors.get(self.proc_b_state, (NEON_GREEN, BG_DARK))
        self.badge_proc_a.config(text=self.proc_a_state, bg=ab, fg=af)
        self.badge_proc_b.config(text=self.proc_b_state, bg=bb, fg=bf)

        # Quick stats
        self.quick_stats_label.config(
            text=f"MAILBOX: {self.buffer.count}/{self.buffer.capacity} | "
                 f"MUTEX: {self.buffer.mutex} | EMPTY: {self.buffer.empty_sem} | FULL: {self.buffer.full_sem}"
        )

        # Check Mission 4 (Balanced ticks)
        if self.auto_producer_active and self.auto_consumer_active:
            occupancy = self.buffer.count / self.buffer.capacity
            if 0.3 <= occupancy <= 0.7:
                self.mission_flags["m4_balanced_ticks"] += 1
                if self.mission_flags["m4_balanced_ticks"] >= 50:
                    self._update_mission_ui()
            else:
                self.mission_flags["m4_balanced_ticks"] = max(0, self.mission_flags["m4_balanced_ticks"] - 1)

    def _inspect_packet(self, p: MessagePacket):
        self.lbl_insp_id.config(text=f"ID: #{p.msg_id:04d} ({p.icon} {p.msg_type})")
        self.lbl_insp_sender.config(text=f"Sender: {p.sender}")
        self.lbl_insp_recv.config(text=f"Receiver: {p.receiver}")
        self.lbl_insp_time.config(text=f"Timestamp: {p.timestamp}")
        self.lbl_insp_payload.config(text=f"Payload: \"{p.payload}\"")
        self.lbl_insp_size.config(text=f"Packet Size: {p.size_bytes} Bytes")

    def _log(self, text: str):
        ts = datetime.now().strftime("%H:%M:%S")
        append_text(self.log_txt, f"[{ts}] {text}")

    # ═════════════════════════════════════════════════════════════════════════
    # ANIMATION LOOP & ARENA CANVAS RENDERING
    # ═════════════════════════════════════════════════════════════════════════
    def on_show(self):
        self._animate()

    def on_hide(self):
        if self._anim_id:
            self.after_cancel(self._anim_id)
            self._anim_id = None
        if self._auto_prod_after_id:
            self.after_cancel(self._auto_prod_after_id)
            self._auto_prod_after_id = None
        if self._auto_cons_after_id:
            self.after_cancel(self._auto_cons_after_id)
            self._auto_cons_after_id = None
        for aid in list(self._pending_afters):
            try:
                self.after_cancel(aid)
            except Exception:
                pass
        self._pending_afters.clear()

    def _animate(self):
        self._tick += 1
        self._draw_canvas_scene()
        self._update_pellets()
        self._anim_id = self.after(45, self._animate)

    def _draw_canvas_scene(self):
        c = self.canvas
        c.delete("all")
        w = c.winfo_width()
        h = c.winfo_height()
        if w < 20 or h < 20:
            return

        # ── Arcade Maze Grid Background Dots
        for gx in range(15, w, 28):
            for gy in range(15, h, 28):
                c.create_oval(gx - 1, gy - 1, gx + 1, gy + 1, fill="#121232", outline="")

        # ── Geometry Coordinates
        pac_x = int(w * 0.12)
        pac_y = int(h * 0.40)
        ghost_x = int(w * 0.88)
        ghost_y = int(h * 0.40)
        tube_y = int(h * 0.40)

        buf_x0 = int(w * 0.28)
        buf_x1 = int(w * 0.72)
        buf_y0 = int(h * 0.25)
        buf_y1 = int(h * 0.65)

        # ── Neon Conduit Tubes
        c.create_line(pac_x + 36, tube_y, buf_x0, tube_y, fill=NEON_BLUE, width=4, dash=(10, 4))
        c.create_line(buf_x1, tube_y, ghost_x - 36, tube_y, fill=NEON_BLUE, width=4, dash=(10, 4))

        # ── Pac-Man Producer (PROC-A)
        self._pac_mouth += 4 * self._pac_dir
        if self._pac_mouth >= 55 or self._pac_mouth <= 2:
            self._pac_dir *= -1

        pm_color = NEON_YELLOW
        if self.proc_a_state == ProcessState.BLOCKED:
            pm_color = NEON_RED
        elif self.proc_a_state == ProcessState.SENDING:
            pm_color = NEON_GREEN

        draw_pacman(c, pac_x, pac_y, r=32, mouth_angle=self._pac_mouth, color=pm_color, facing="right", tag="arena_pac")

        c.create_text(pac_x, pac_y - 48, text="PAC-MAN (PROC-A)", font=FONT_BODY, fill=NEON_YELLOW)
        c.create_text(pac_x, pac_y - 34, text="Producer [PID: 101]", font=FONT_SMALL, fill=TEXT_DIM)
        c.create_text(pac_x, pac_y + 44, text=f"[{self.proc_a_state}]",
                      font=FONT_SMALL, fill=NEON_RED if self.proc_a_state == ProcessState.BLOCKED else NEON_GREEN)

        # ── Ghost Consumer (PROC-B)
        self._ghost_bob += 1 * self._ghost_dir
        if abs(self._ghost_bob) >= 5:
            self._ghost_dir *= -1

        ghost_name = self.receiver_var.get()
        ghost_color_map = {"Blinky": NEON_RED, "Pinky": NEON_PINK, "Inky": NEON_BLUE, "Clyde": NEON_ORANGE}
        g_color = ghost_color_map.get(ghost_name, NEON_PINK)

        is_scared = (self.proc_b_state == ProcessState.BLOCKED)
        draw_ghost(c, ghost_x, ghost_y + self._ghost_bob, r=30, color=g_color,
                   look_dir="left", scared=is_scared, tag="arena_ghost")

        c.create_text(ghost_x, ghost_y - 48, text=f"{ghost_name.upper()} (PROC-B)", font=FONT_BODY, fill=g_color)
        c.create_text(ghost_x, ghost_y - 34, text="Consumer [PID: 202]", font=FONT_SMALL, fill=TEXT_DIM)
        c.create_text(ghost_x, ghost_y + 48, text=f"[{self.proc_b_state}]",
                      font=FONT_SMALL, fill=NEON_RED if self.proc_b_state == ProcessState.BLOCKED else NEON_GREEN)

        # ── Bounded Buffer (Mailbox Slots)
        self._draw_mailbox_buffer(c, buf_x0, buf_y0, buf_x1, buf_y1)

        # ── Traveling Pellets Animation
        for pel in self._pellets_traveling:
            direction = pel["type"]
            prog = pel["progress"]
            icon = pel["icon"]
            packet = pel["packet"]

            if direction == "send":
                start_x = pac_x + 36
                end_x = buf_x0
                cur_x = start_x + (end_x - start_x) * prog
            else:
                start_x = buf_x1
                end_x = ghost_x - 36
                cur_x = start_x + (end_x - start_x) * prog

            # Pellet glow & icon
            c.create_oval(cur_x - 12, tube_y - 12, cur_x + 12, tube_y + 12, fill=BG_CARD, outline=NEON_YELLOW, width=2)
            c.create_text(cur_x, tube_y, text=icon, font=("Segoe UI Emoji", 12))
            c.create_text(cur_x, tube_y - 18, text=f"#{packet.msg_id}", font=FONT_SMALL, fill=NEON_YELLOW)

    def _draw_mailbox_buffer(self, c: tk.Canvas, x0: int, y0: int, x1: int, y1: int):
        """Draw the animated circular mailbox buffer slots."""
        cap = self.buffer.capacity
        slots = self.buffer.peek_slots()
        head = self.buffer.head
        tail = self.buffer.tail

        # Outer casing
        border_col = NEON_RED if self.buffer.is_full else (NEON_BLUE if self.buffer.is_empty else NEON_YELLOW)
        c.create_rectangle(x0, y0, x1, y1, fill=BG_CARD, outline=border_col, width=2)

        # Header bar with capacity gauge
        c.create_rectangle(x0, y0, x1, y0 + 22, fill=BG_PANEL, outline=border_col)
        gauge_text = f"MAILBOX BUFFER (CAPACITY: {self.buffer.count}/{cap})"
        c.create_text((x0 + x1) // 2, y0 + 11, text=gauge_text, font=FONT_SMALL, fill=NEON_YELLOW)

        # Compute slot widths
        pad = 6
        avail_w = (x1 - x0) - pad * 2
        slot_w = avail_w / cap
        slot_h = (y1 - y0) - 28 - pad * 2

        self.slot_rects = []
        for i in range(cap):
            sx = x0 + pad + i * slot_w
            sy = y0 + 26 + pad
            ex = sx + slot_w - 4
            ey = sy + slot_h

            self.slot_rects.append((sx, sy, ex, ey, i))

            packet = slots[i]
            if packet is not None:
                # Filled slot (Glowing neon box)
                c.create_rectangle(sx, sy, ex, ey, fill="#262200", outline=NEON_YELLOW, width=2)
                c.create_text((sx + ex) / 2, (sy + ey) / 2 - 12, text=packet.icon, font=("Segoe UI Emoji", 14))
                short_p = packet.payload if len(packet.payload) <= 6 else packet.payload[:5] + ".."
                c.create_text((sx + ex) / 2, (sy + ey) / 2 + 6, text=short_p, font=FONT_SMALL, fill=TEXT_WHITE)
                c.create_text((sx + ex) / 2, (sy + ey) / 2 + 20, text=f"#{packet.msg_id}", font=FONT_SMALL, fill=NEON_YELLOW)
            else:
                # Empty slot
                c.create_rectangle(sx, sy, ex, ey, fill=BG_DARK, outline="#222244", width=1, dash=(3, 3))
                c.create_text((sx + ex) / 2, (sy + ey) / 2, text=f"[{i}]", font=FONT_SMALL, fill=TEXT_DIM)

            # In/Out Pointers
            if i == tail and not self.buffer.is_full:
                c.create_text((sx + ex) / 2, sy - 8, text="▼ IN", font=FONT_SMALL, fill=NEON_GREEN)
            if i == head and not self.buffer.is_empty:
                c.create_text((sx + ex) / 2, ey + 8, text="▲ OUT", font=FONT_SMALL, fill=NEON_BLUE)

        # Warning Bar below buffer
        if self.buffer.is_full:
            c.create_text((x0 + x1) // 2, y1 + 16,
                          text="⚠ BUFFER FULL! Producer blocked on wait(empty)",
                          font=FONT_BODY, fill=NEON_RED)
        elif self.buffer.is_empty:
            c.create_text((x0 + x1) // 2, y1 + 16,
                          text="⚠ BUFFER EMPTY! Consumer blocked on wait(full)",
                          font=FONT_BODY, fill=NEON_ORANGE)

    def _update_pellets(self):
        new_list = []
        for pel in self._pellets_traveling:
            pel["progress"] += 0.05
            if pel["progress"] < 1.0:
                new_list.append(pel)
            else:
                # Arrived at destination
                if pel["type"] == "send":
                    if self.proc_a_state == ProcessState.SENDING:
                        self.proc_a_state = ProcessState.RUNNING
                elif pel["type"] == "recv":
                    if self.proc_b_state == ProcessState.RECEIVING:
                        self.proc_b_state = ProcessState.RUNNING
                self._update_semaphores_ui()
        self._pellets_traveling = new_list

    def _on_canvas_click(self, event):
        """Handle clicking on mailbox slots to inspect packets."""
        slots = self.buffer.peek_slots()
        for sx, sy, ex, ey, idx in getattr(self, "slot_rects", []):
            if sx <= event.x <= ex and sy <= event.y <= ey:
                if idx < len(slots) and slots[idx] is not None:
                    self._inspect_packet(slots[idx])
                    SOUND_ENGINE.play_send()
                break


# ─────────────────────────────────────────────────────────────────────────────
# 6. MODULE 2: CPU SCHEDULING ARCADE
# ─────────────────────────────────────────────────────────────────────────────

class CPUSchedulingModule(tk.Frame):
    """Interactive CPU Scheduling simulation (FCFS, SJF, Round Robin)."""

    def __init__(self, parent):
        super().__init__(parent, bg=BG_DARK)
        self.algorithm = tk.StringVar(value="Round Robin")
        self.quantum = tk.IntVar(value=3)
        self.processes = [
            {"id": "P1", "burst": 6, "remain": 6, "color": NEON_RED, "name": "Blinky"},
            {"id": "P2", "burst": 4, "remain": 4, "color": NEON_PINK, "name": "Pinky"},
            {"id": "P3", "burst": 8, "remain": 8, "color": NEON_BLUE, "name": "Inky"},
            {"id": "P4", "burst": 3, "remain": 3, "color": NEON_ORANGE, "name": "Clyde"},
        ]
        self.timeline = []
        self.current_time = 0
        self._anim_id = None
        self._running = False
        self._build_ui()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=BG_PANEL, pady=6)
        hdr.pack(fill="x")
        tk.Label(hdr, text="◄ MODULE 2: CPU SCHEDULING ARCADE ►", font=FONT_HEADER, bg=BG_PANEL, fg=NEON_BLUE).pack()
        tk.Label(hdr, text="Pac-Man CPU eats process bursts on the Gantt Chart timeline!", font=FONT_SMALL, bg=BG_PANEL, fg=TEXT_DIM).pack()

        body = tk.Frame(self, bg=BG_DARK)
        body.pack(fill="both", expand=True, padx=12, pady=8)

        # Left Controls
        left = tk.Frame(body, bg=BG_CARD, width=240, bd=1, relief="flat", padx=10, pady=8)
        left.pack(side="left", fill="y", padx=(0, 8))
        left.pack_propagate(False)

        tk.Label(left, text="[ SCHEDULER CONTROLS ]", font=FONT_BODY, bg=BG_CARD, fg=NEON_BLUE).pack(pady=(4, 6))

        tk.Label(left, text="Algorithm:", font=FONT_SMALL, bg=BG_CARD, fg=TEXT_WHITE).pack(anchor="w")
        algo_menu = tk.OptionMenu(left, self.algorithm, "Round Robin", "FCFS (First-Come First-Served)", "SJF (Shortest Job First)")
        algo_menu.config(bg=BG_DARK, fg=NEON_YELLOW, font=FONT_SMALL, bd=0, relief="flat")
        algo_menu["menu"].config(bg=BG_DARK, fg=NEON_YELLOW, font=FONT_SMALL)
        algo_menu.pack(fill="x", pady=4)

        tk.Label(left, text="Time Quantum (RR):", font=FONT_SMALL, bg=BG_CARD, fg=TEXT_WHITE).pack(anchor="w", pady=(6, 0))
        tk.Scale(left, from_=1, to=6, orient="horizontal", variable=self.quantum,
                 bg=BG_CARD, fg=NEON_YELLOW, troughcolor=BG_DARK, font=FONT_SMALL, highlightthickness=0).pack(fill="x")

        neon_button(left, "▶ RUN SIMULATION", self.run_simulation, color=NEON_GREEN, width=18).pack(pady=6, fill="x")
        neon_button(left, "⏯ STEP FORWARD", self.step_simulation, color=NEON_YELLOW, width=18).pack(pady=4, fill="x")
        neon_button(left, "↺ RESET PROCESSES", self.reset_sim, color=NEON_PINK, width=18).pack(pady=4, fill="x")

        # Process list display
        tk.Label(left, text="\n[ PROCESS QUEUE ]", font=FONT_SMALL, bg=BG_CARD, fg=TEXT_DIM).pack(anchor="w")
        self.lbl_proc_list = tk.Label(left, text="", font=FONT_CODE, bg=BG_CARD, fg=TEXT_WHITE, justify="left")
        self.lbl_proc_list.pack(fill="x", pady=4)
        self._update_proc_list_ui()

        # Center Canvas: Gantt chart + Pac-Man CPU eater
        center = tk.Frame(body, bg=BG_DARK)
        center.pack(side="left", fill="both", expand=True)

        self.canvas = tk.Canvas(center, bg=BG_DARK, bd=0, highlightthickness=2, highlightbackground=NEON_BLUE)
        self.canvas.pack(fill="both", expand=True)

        # Bottom stats
        self.stats_bar = tk.Label(self, text="Current Time: 0 | CPU: IDLE | Ready Queue: [P1, P2, P3, P4]",
                                  font=FONT_SMALL, bg=BG_PANEL, fg=NEON_GREEN, pady=4)
        self.stats_bar.pack(fill="x", side="bottom")

    def _update_proc_list_ui(self):
        lines = []
        for p in self.processes:
            lines.append(f"{p['id']} ({p['name']}): Burst={p['burst']}, Rem={p['remain']}")
        self.lbl_proc_list.config(text="\n".join(lines))

    def run_simulation(self):
        self._running = True
        self._step_loop()

    def _step_loop(self):
        if not self._running:
            return
        done = self.step_simulation()
        if not done:
            self._anim_id = self.after(500, self._step_loop)

    def step_simulation(self) -> bool:
        # Check if all processes complete
        active = [p for p in self.processes if p["remain"] > 0]
        if not active:
            self._running = False
            self.stats_bar.config(text=f"ALL PROCESSES COMPLETE! Total Time: {self.current_time} cycles.")
            SOUND_ENGINE.play_success()
            return True

        algo = self.algorithm.get()
        if "FCFS" in algo:
            cur_p = active[0]
            exec_time = 1
        elif "SJF" in algo:
            active.sort(key=lambda p: p["remain"])
            cur_p = active[0]
            exec_time = 1
        else:  # Round Robin
            cur_p = active[0]
            exec_time = 1

        cur_p["remain"] -= exec_time
        self.timeline.append((cur_p["id"], cur_p["color"], self.current_time))
        self.current_time += exec_time
        SOUND_ENGINE.play_send()

        # If Round Robin and still has burst, rotate to end
        if "Round Robin" in algo and cur_p["remain"] > 0:
            self.processes.remove(cur_p)
            self.processes.append(cur_p)

        self._draw_gantt()
        self._update_proc_list_ui()
        self.stats_bar.config(text=f"Current Time: {self.current_time} | Executing: {cur_p['id']} ({cur_p['name']}) | Remaining: {cur_p['remain']}")
        return False

    def reset_sim(self):
        self._running = False
        if self._anim_id:
            self.after_cancel(self._anim_id)
            self._anim_id = None
        self.current_time = 0
        self.timeline.clear()
        for p in self.processes:
            p["remain"] = p["burst"]
        self._draw_gantt()
        self._update_proc_list_ui()
        self.stats_bar.config(text="Simulation Reset. Ready to run.")

    def _draw_gantt(self):
        c = self.canvas
        c.delete("all")
        w = c.winfo_width()
        h = c.winfo_height()
        if w < 20:
            return

        # Title
        c.create_text(w // 2, 30, text=f"CPU GANTT CHART ({self.algorithm.get()})", font=FONT_HEADER, fill=NEON_YELLOW)

        # Pac-Man CPU eater
        pac_x = min(w - 60, 60 + len(self.timeline) * 28)
        draw_pacman(c, pac_x, 100, r=26, mouth_angle=40, color=NEON_YELLOW, tag="cpu_pac")
        c.create_text(pac_x, 140, text="CPU Core", font=FONT_SMALL, fill=NEON_YELLOW)

        # Gantt timeline bar
        gx0 = 50
        gy0 = 180
        gy1 = 230
        for i, (pid, col, t) in enumerate(self.timeline):
            bx0 = gx0 + i * 28
            bx1 = bx0 + 26
            c.create_rectangle(bx0, gy0, bx1, gy1, fill=col, outline=BG_DARK, width=2)
            c.create_text((bx0 + bx1) / 2, (gy0 + gy1) / 2, text=pid, font=FONT_SMALL, fill=BG_DARK)
            c.create_text(bx0, gy1 + 12, text=str(t), font=FONT_SMALL, fill=TEXT_DIM)

    def on_show(self):
        self._draw_gantt()

    def on_hide(self):
        self._running = False
        if self._anim_id:
            self.after_cancel(self._anim_id)


# ─────────────────────────────────────────────────────────────────────────────
# 7. MODULE 3: MEMORY MANAGEMENT ARCADE
# ─────────────────────────────────────────────────────────────────────────────

class MemoryManagementModule(tk.Frame):
    """Interactive Memory Management (Paging & Contiguous Allocation)."""

    def __init__(self, parent):
        super().__init__(parent, bg=BG_DARK)
        self.total_frames = 16
        self.frames = [None] * self.total_frames  # None or process name
        self.algo = tk.StringVar(value="First-Fit")
        self._build_ui()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=BG_PANEL, pady=6)
        hdr.pack(fill="x")
        tk.Label(hdr, text="◄ MODULE 3: MEMORY MANAGEMENT ARCADE ►", font=FONT_HEADER, bg=BG_PANEL, fg=NEON_GREEN).pack()
        tk.Label(hdr, text="Allocate memory blocks in the Pac-Man physical frame grid!", font=FONT_SMALL, bg=BG_PANEL, fg=TEXT_DIM).pack()

        body = tk.Frame(self, bg=BG_DARK)
        body.pack(fill="both", expand=True, padx=12, pady=8)

        left = tk.Frame(body, bg=BG_CARD, width=240, bd=1, relief="flat", padx=10, pady=8)
        left.pack(side="left", fill="y", padx=(0, 8))
        left.pack_propagate(False)

        tk.Label(left, text="[ ALLOCATION CONTROLS ]", font=FONT_BODY, bg=BG_CARD, fg=NEON_GREEN).pack(pady=(4, 6))

        tk.Label(left, text="Process Name:", font=FONT_SMALL, bg=BG_CARD, fg=TEXT_WHITE).pack(anchor="w")
        self.entry_proc = tk.Entry(left, bg=BG_DARK, fg=NEON_YELLOW, font=FONT_BODY, bd=0, highlightthickness=1)
        self.entry_proc.insert(0, "P1 (Pac-Man)")
        self.entry_proc.pack(fill="x", pady=2)

        tk.Label(left, text="Required Frames (1-6):", font=FONT_SMALL, bg=BG_CARD, fg=TEXT_WHITE).pack(anchor="w", pady=(4, 0))
        self.spin_size = tk.Spinbox(left, from_=1, to=6, bg=BG_DARK, fg=NEON_GREEN, font=FONT_BODY, bd=0)
        self.spin_size.pack(fill="x", pady=2)

        neon_button(left, "➕ ALLOCATE FRAMES", self.do_allocate, color=NEON_GREEN, width=18).pack(pady=6, fill="x")
        neon_button(left, "➖ DEALLOCATE FIRST", self.do_deallocate, color=NEON_RED, width=18).pack(pady=4, fill="x")
        neon_button(left, "↺ RESET MEMORY", self.do_reset, color=NEON_PINK, width=18).pack(pady=4, fill="x")

        # Canvas for grid of 16 memory frames
        center = tk.Frame(body, bg=BG_DARK)
        center.pack(side="left", fill="both", expand=True)

        self.canvas = tk.Canvas(center, bg=BG_DARK, bd=0, highlightthickness=2, highlightbackground=NEON_GREEN)
        self.canvas.pack(fill="both", expand=True)

        self.status = tk.Label(self, text="Total Memory: 16 Frames (64 KB) | Free: 16 Frames",
                               font=FONT_SMALL, bg=BG_PANEL, fg=NEON_GREEN, pady=4)
        self.status.pack(fill="x", side="bottom")

    def do_allocate(self):
        name = self.entry_proc.get().strip()
        try:
            sz = int(self.spin_size.get())
        except ValueError:
            return

        free_indices = [i for i, f in enumerate(self.frames) if f is None]
        if len(free_indices) < sz:
            SOUND_ENGINE.play_blocked()
            self.status.config(text=f"⚠ OUT OF MEMORY: Requested {sz} frames, but only {len(free_indices)} free!")
            return

        # First-fit allocation
        for idx in free_indices[:sz]:
            self.frames[idx] = name

        SOUND_ENGINE.play_send()
        self._draw_grid()
        free_count = self.frames.count(None)
        self.status.config(text=f"Allocated {sz} frames to {name}. Free: {free_count} Frames")

    def do_deallocate(self):
        allocated = [f for f in self.frames if f is not None]
        if not allocated:
            return
        target = allocated[0]
        for i in range(self.total_frames):
            if self.frames[i] == target:
                self.frames[i] = None
        SOUND_ENGINE.play_receive()
        self._draw_grid()
        free_count = self.frames.count(None)
        self.status.config(text=f"Deallocated {target}. Free: {free_count} Frames")

    def do_reset(self):
        self.frames = [None] * self.total_frames
        self._draw_grid()
        self.status.config(text="Memory Reset: All 16 frames are free.")

    def _draw_grid(self):
        c = self.canvas
        c.delete("all")
        w = c.winfo_width()
        h = c.winfo_height()
        if w < 20:
            return

        c.create_text(w // 2, 30, text="PHYSICAL MEMORY FRAME MATRIX (4x4 GRID)", font=FONT_HEADER, fill=NEON_GREEN)

        cols = 4
        rows = 4
        box_w = 90
        box_h = 60
        start_x = (w - (cols * (box_w + 10))) // 2
        start_y = 70

        for i in range(self.total_frames):
            r = i // cols
            col = i % cols
            x0 = start_x + col * (box_w + 10)
            y0 = start_y + r * (box_h + 10)
            x1 = x0 + box_w
            y1 = y0 + box_h

            owner = self.frames[i]
            if owner is None:
                c.create_rectangle(x0, y0, x1, y1, fill=BG_CARD, outline=TEXT_DIM, dash=(2, 2))
                c.create_text((x0 + x1) / 2, (y0 + y1) / 2, text=f"Frame {i}\n[FREE]", font=FONT_SMALL, fill=TEXT_DIM)
            else:
                c.create_rectangle(x0, y0, x1, y1, fill="#003D1A", outline=NEON_GREEN, width=2)
                c.create_text((x0 + x1) / 2, (y0 + y1) / 2, text=f"Frame {i}\n{owner[:8]}", font=FONT_SMALL, fill=NEON_GREEN)

    def on_show(self):
        self._draw_grid()


# ─────────────────────────────────────────────────────────────────────────────
# 8. MODULE 4: DEADLOCK & SYNCHRONIZATION ARCADE
# ─────────────────────────────────────────────────────────────────────────────

class DeadlockModule(tk.Frame):
    """Interactive Dining Philosophers & Deadlock Detection simulator."""

    def __init__(self, parent):
        super().__init__(parent, bg=BG_DARK)
        self.ghost_states = ["THINKING"] * 4
        self.fork_owners = [None] * 4  # 4 power chopsticks/forks
        self.deadlocked = False
        self._build_ui()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=BG_PANEL, pady=6)
        hdr.pack(fill="x")
        tk.Label(hdr, text="◄ MODULE 4: DEADLOCK & DINING PHILOSOPHERS ►", font=FONT_HEADER, bg=BG_PANEL, fg=NEON_RED).pack()
        tk.Label(hdr, text="4 Ghosts competing for 4 Power Chopsticks. Demonstrates Circular Wait!", font=FONT_SMALL, bg=BG_PANEL, fg=TEXT_DIM).pack()

        body = tk.Frame(self, bg=BG_DARK)
        body.pack(fill="both", expand=True, padx=12, pady=8)

        left = tk.Frame(body, bg=BG_CARD, width=240, bd=1, relief="flat", padx=10, pady=8)
        left.pack(side="left", fill="y", padx=(0, 8))
        left.pack_propagate(False)

        tk.Label(left, text="[ COFFMAN CONDITIONS ]", font=FONT_BODY, bg=BG_CARD, fg=NEON_RED).pack(pady=(4, 6))
        neon_button(left, "⚡ TRIGGER DEADLOCK", self.trigger_deadlock, color=NEON_RED, width=18).pack(pady=4, fill="x")
        neon_button(left, "🛡️ DEADLOCK PREVENTION", self.prevent_deadlock, color=NEON_GREEN, width=18).pack(pady=4, fill="x")
        neon_button(left, "↺ RESET TABLE", self.reset_table, color=NEON_PINK, width=18).pack(pady=4, fill="x")

        tk.Label(left, text="\nCoffman's 4 Conditions:\n1. Mutual Exclusion\n2. Hold and Wait\n3. No Preemption\n4. Circular Wait",
                 font=FONT_SMALL, bg=BG_CARD, fg=TEXT_WHITE, justify="left").pack(anchor="w")

        center = tk.Frame(body, bg=BG_DARK)
        center.pack(side="left", fill="both", expand=True)

        self.canvas = tk.Canvas(center, bg=BG_DARK, bd=0, highlightthickness=2, highlightbackground=NEON_RED)
        self.canvas.pack(fill="both", expand=True)

        self.status = tk.Label(self, text="Status: NORMAL (Ghosts are thinking peacefully)",
                               font=FONT_SMALL, bg=BG_PANEL, fg=NEON_GREEN, pady=4)
        self.status.pack(fill="x", side="bottom")

    def trigger_deadlock(self):
        # Every ghost holds left fork and waits for right fork -> Classic Circular Wait!
        self.fork_owners = [0, 1, 2, 3]
        self.ghost_states = ["BLOCKED (Waiting right fork)"] * 4
        self.deadlocked = True
        SOUND_ENGINE.play_blocked()
        self._draw_table()
        self.status.config(text="⚠ DEADLOCK OCCURRED! All 4 ghosts hold 1 fork and wait indefinitely (Circular Wait).", fg=NEON_RED)

    def prevent_deadlock(self):
        # Resource hierarchy prevention (Ghost 3 picks right fork first)
        self.fork_owners = [0, 0, None, 2]
        self.ghost_states = ["EATING", "THINKING", "EATING", "THINKING"]
        self.deadlocked = False
        SOUND_ENGINE.play_success()
        self._draw_table()
        self.status.config(text="✔ DEADLOCK PREVENTED! Resource hierarchy broken; ghosts eating smoothly.", fg=NEON_GREEN)

    def reset_table(self):
        self.fork_owners = [None] * 4
        self.ghost_states = ["THINKING"] * 4
        self.deadlocked = False
        self._draw_table()
        self.status.config(text="Table Reset. All ghosts are thinking.")

    def _draw_table(self):
        c = self.canvas
        c.delete("all")
        w = c.winfo_width()
        h = c.winfo_height()
        if w < 20:
            return

        cx, cy = w // 2, h // 2
        # Dining table
        t_col = NEON_RED if self.deadlocked else NEON_BLUE
        c.create_oval(cx - 110, cy - 110, cx + 110, cy + 110, fill=BG_CARD, outline=t_col, width=3)
        c.create_text(cx, cy, text="DINING\nTABLE", font=FONT_BODY, fill=t_col, justify="center")

        # 4 Ghosts positioned around table (North, East, South, West)
        positions = [
            (cx, cy - 160, "Blinky", NEON_RED),
            (cx + 170, cy, "Pinky", NEON_PINK),
            (cx, cy + 160, "Inky", NEON_BLUE),
            (cx - 170, cy, "Clyde", NEON_ORANGE),
        ]
        for idx, (gx, gy, name, col) in enumerate(positions):
            draw_ghost(c, gx, gy, r=22, color=col, tag=f"ph_g_{idx}")
            c.create_text(gx, gy + 32, text=f"{name}\n[{self.ghost_states[idx]}]", font=FONT_SMALL, fill=col, justify="center")

    def on_show(self):
        self._draw_table()


# ─────────────────────────────────────────────────────────────────────────────
# 9. MODULE 5: FILE SYSTEMS ARCADE
# ─────────────────────────────────────────────────────────────────────────────

class FileSystemsModule(tk.Frame):
    """Interactive File System Inode & Disk Sector Visualizer."""

    def __init__(self, parent):
        super().__init__(parent, bg=BG_DARK)
        self.sectors = [None] * 12
        self.files = [
            {"name": "pacman.sav", "icon": "🟡", "sectors": [0, 1]},
            {"name": "cherry.bmp", "icon": "🍒", "sectors": [3, 4, 5]},
        ]
        self._build_ui()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=BG_PANEL, pady=6)
        hdr.pack(fill="x")
        tk.Label(hdr, text="◄ MODULE 5: FILE SYSTEMS & INODES ARCADE ►", font=FONT_HEADER, bg=BG_PANEL, fg=NEON_ORANGE).pack()
        tk.Label(hdr, text="Simulates Inode index blocks and disk sector allocation!", font=FONT_SMALL, bg=BG_PANEL, fg=TEXT_DIM).pack()

        body = tk.Frame(self, bg=BG_DARK)
        body.pack(fill="both", expand=True, padx=12, pady=8)

        left = tk.Frame(body, bg=BG_CARD, width=240, bd=1, relief="flat", padx=10, pady=8)
        left.pack(side="left", fill="y", padx=(0, 8))
        left.pack_propagate(False)

        tk.Label(left, text="[ DISK OPERATIONS ]", font=FONT_BODY, bg=BG_CARD, fg=NEON_ORANGE).pack(pady=(4, 6))
        neon_button(left, "➕ CREATE GHOST.DAT", self.create_file, color=NEON_YELLOW, width=18).pack(pady=4, fill="x")
        neon_button(left, "➖ DELETE CHERRY.BMP", self.delete_file, color=NEON_RED, width=18).pack(pady=4, fill="x")
        neon_button(left, "↺ FORMAT DISK", self.format_disk, color=NEON_PINK, width=18).pack(pady=4, fill="x")

        center = tk.Frame(body, bg=BG_DARK)
        center.pack(side="left", fill="both", expand=True)

        self.canvas = tk.Canvas(center, bg=BG_DARK, bd=0, highlightthickness=2, highlightbackground=NEON_ORANGE)
        self.canvas.pack(fill="both", expand=True)

        self.status = tk.Label(self, text="Disk Capacity: 12 Sectors (48 KB) | File System: RetroFS",
                               font=FONT_SMALL, bg=BG_PANEL, fg=NEON_ORANGE, pady=4)
        self.status.pack(fill="x", side="bottom")

    def create_file(self):
        new_f = {"name": "ghost.dat", "icon": "👻", "sectors": [7, 8]}
        if not any(f["name"] == "ghost.dat" for f in self.files):
            self.files.append(new_f)
            SOUND_ENGINE.play_send()
            self._draw_disk()
            self.status.config(text="Created ghost.dat (Allocated sectors [7, 8])")

    def delete_file(self):
        self.files = [f for f in self.files if f["name"] != "cherry.bmp"]
        SOUND_ENGINE.play_receive()
        self._draw_disk()
        self.status.config(text="Deleted cherry.bmp (Freed sectors [3, 4, 5])")

    def format_disk(self):
        self.files.clear()
        self._draw_disk()
        self.status.config(text="Formatted disk. All sectors free.")

    def _draw_disk(self):
        c = self.canvas
        c.delete("all")
        w = c.winfo_width()
        h = c.winfo_height()
        if w < 20:
            return

        c.create_text(w // 2, 30, text="DISK SECTOR MAP (INODE BLOCKS)", font=FONT_HEADER, fill=NEON_ORANGE)

        # Draw 12 circular disk sectors
        cx, cy = w // 2, h // 2
        r_outer = 130
        for i in range(12):
            angle = (i * 30) * (math.pi / 180)
            sx = cx + r_outer * math.cos(angle)
            sy = cy + r_outer * math.sin(angle)

            # Find if occupied
            owner = None
            for f in self.files:
                if i in f["sectors"]:
                    owner = f
                    break

            if owner:
                c.create_oval(sx - 18, sy - 18, sx + 18, sy + 18, fill="#4D2600", outline=NEON_ORANGE, width=2)
                c.create_text(sx, sy, text=owner["icon"], font=("Segoe UI Emoji", 10))
            else:
                c.create_oval(sx - 18, sy - 18, sx + 18, sy + 18, fill=BG_CARD, outline=TEXT_DIM, dash=(2, 2))
                c.create_text(sx, sy, text=str(i), font=FONT_SMALL, fill=TEXT_DIM)

    def on_show(self):
        self._draw_disk()


# ─────────────────────────────────────────────────────────────────────────────
# 10. MODULE 6: PROCESS MANAGEMENT ARCADE
# ─────────────────────────────────────────────────────────────────────────────

class ProcessManagementModule(tk.Frame):
    """Interactive 5-State Process Lifecycle & PCB Inspector."""

    def __init__(self, parent):
        super().__init__(parent, bg=BG_DARK)
        self.state = "READY"
        self.pcb = {
            "pid": 101,
            "name": "PacManKernel",
            "state": "READY",
            "pc": "0x0040",
            "regs": "AX=0, BX=5",
            "mem": "64 KB"
        }
        self._build_ui()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=BG_PANEL, pady=6)
        hdr.pack(fill="x")
        tk.Label(hdr, text="◄ MODULE 6: PROCESS MANAGEMENT ARCADE ►", font=FONT_HEADER, bg=BG_PANEL, fg=NEON_PURPLE).pack()
        tk.Label(hdr, text="5-State Process Lifecycle (New -> Ready -> Running -> Waiting -> Terminated)", font=FONT_SMALL, bg=BG_PANEL, fg=TEXT_DIM).pack()

        body = tk.Frame(self, bg=BG_DARK)
        body.pack(fill="both", expand=True, padx=12, pady=8)

        left = tk.Frame(body, bg=BG_CARD, width=240, bd=1, relief="flat", padx=10, pady=8)
        left.pack(side="left", fill="y", padx=(0, 8))
        left.pack_propagate(False)

        tk.Label(left, text="[ STATE TRANSITIONS ]", font=FONT_BODY, bg=BG_CARD, fg=NEON_PURPLE).pack(pady=(4, 6))
        neon_button(left, "▶ DISPATCH (To Run)", lambda: self._transition("RUNNING"), color=NEON_GREEN, width=18).pack(pady=4, fill="x")
        neon_button(left, "⏸ I/O WAIT (To Wait)", lambda: self._transition("WAITING"), color=NEON_ORANGE, width=18).pack(pady=4, fill="x")
        neon_button(left, "✔ I/O DONE (To Ready)", lambda: self._transition("READY"), color=NEON_YELLOW, width=18).pack(pady=4, fill="x")
        neon_button(left, "⏹ TERMINATE", lambda: self._transition("TERMINATED"), color=NEON_RED, width=18).pack(pady=4, fill="x")
        neon_button(left, "↺ NEW PROCESS", lambda: self._transition("NEW"), color=NEON_PINK, width=18).pack(pady=4, fill="x")

        # PCB Inspector
        tk.Label(left, text="\n[ PCB INSPECTOR ]", font=FONT_SMALL, bg=BG_CARD, fg=TEXT_DIM).pack(anchor="w")
        self.lbl_pcb = tk.Label(left, text="", font=FONT_CODE, bg=BG_CARD, fg=TEXT_WHITE, justify="left")
        self.lbl_pcb.pack(fill="x", pady=4)
        self._update_pcb_ui()

        center = tk.Frame(body, bg=BG_DARK)
        center.pack(side="left", fill="both", expand=True)

        self.canvas = tk.Canvas(center, bg=BG_DARK, bd=0, highlightthickness=2, highlightbackground=NEON_PURPLE)
        self.canvas.pack(fill="both", expand=True)

        self.status = tk.Label(self, text="Process State Machine Active.",
                               font=FONT_SMALL, bg=BG_PANEL, fg=NEON_PURPLE, pady=4)
        self.status.pack(fill="x", side="bottom")

    def _transition(self, new_st: str):
        self.state = new_st
        self.pcb["state"] = new_st
        if new_st == "RUNNING":
            SOUND_ENGINE.play_send()
        elif new_st == "WAITING":
            SOUND_ENGINE.play_blocked()
        elif new_st == "TERMINATED":
            SOUND_ENGINE.play_quiz_wrong()
        else:
            SOUND_ENGINE.play_receive()
        self._update_pcb_ui()
        self._draw_state_machine()
        self.status.config(text=f"Process transitioned to: {new_st}")

    def _update_pcb_ui(self):
        text = (f"PID:  {self.pcb['pid']}\n"
                f"NAME: {self.pcb['name']}\n"
                f"STAT: {self.pcb['state']}\n"
                f"PC:   {self.pcb['pc']}\n"
                f"REGS: {self.pcb['regs']}\n"
                f"MEM:  {self.pcb['mem']}")
        self.lbl_pcb.config(text=text)

    def _draw_state_machine(self):
        c = self.canvas
        c.delete("all")
        w = c.winfo_width()
        h = c.winfo_height()
        if w < 20:
            return

        states = ["NEW", "READY", "RUNNING", "WAITING", "TERMINATED"]
        coords = [
            (80, h // 2),
            (220, h // 2),
            (380, h // 2),
            (300, h // 2 + 100),
            (520, h // 2),
        ]

        # Draw states
        for st, (x, y) in zip(states, coords):
            is_active = (st == self.state)
            fill_col = "#3D004D" if is_active else BG_CARD
            border_col = NEON_PURPLE if is_active else TEXT_DIM
            c.create_rectangle(x - 45, y - 25, x + 45, y + 25, fill=fill_col, outline=border_col, width=2 if is_active else 1)
            c.create_text(x, y, text=st, font=FONT_BODY, fill=NEON_YELLOW if is_active else TEXT_WHITE)

        # Draw Pac-Man marker at current state
        idx = states.index(self.state)
        px, py = coords[idx]
        draw_pacman(c, px, py - 45, r=16, mouth_angle=35, color=NEON_YELLOW, tag="proc_pac")

    def on_show(self):
        self._draw_state_machine()


# ─────────────────────────────────────────────────────────────────────────────
# 11. MAIN MENU & INTEGRATED DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────

class MainMenuFrame(tk.Frame):
    """Animated arcade main menu / dashboard for all 6 modules."""

    def __init__(self, parent, navigate_cb):
        super().__init__(parent, bg=BG_DARK)
        self.navigate = navigate_cb
        self._tick = 0
        self._anim_id = None
        self._mouth = 0
        self._mouth_dir = 1
        self._build_ui()

    def _build_ui(self):
        # Top banner canvas (compact height for 768p and 1080p screens)
        self.tc = tk.Canvas(self, bg=BG_DARK, height=85, highlightthickness=0)
        self.tc.pack(fill="x", pady=(2, 0))

        sub = tk.Label(self, text="● INSERT COIN ● SELECT SIMULATION MODULE ● PRESS START ●",
                       font=FONT_SMALL, bg=BG_DARK, fg=NEON_BLUE)
        sub.pack(pady=(0, 4))

        # 6 Module Cards Grid
        grid = tk.Frame(self, bg=BG_DARK)
        grid.pack(fill="both", expand=True, padx=20, pady=4)

        modules = [
            ("IPC & SYNC\nARCADE",     "Module 1: Message Passing & Synchronization", NEON_YELLOW, "ipc_sync",    "🟡"),
            ("CPU SCHEDULING\nARCADE", "Module 2: FCFS, SJF & Round Robin",           NEON_BLUE,   "cpu_sched",   "⚡"),
            ("MEMORY MGMT\nARCADE",    "Module 3: Paging & Memory Frames",            NEON_GREEN,  "mem_mgmt",    "💾"),
            ("DEADLOCK\nARCADE",       "Module 4: Dining Philosophers & Mutex",       NEON_RED,    "deadlock",    "🔒"),
            ("FILE SYSTEMS\nARCADE",   "Module 5: Inode Allocation & Disk Sectors",   NEON_ORANGE, "file_sys",    "📁"),
            ("PROCESS MGMT\nARCADE",   "Module 6: 5-State Process Machine & PCB",     NEON_PURPLE, "proc_mgmt",   "⚙️"),
        ]

        self.cards = []
        for idx, (title, desc, color, key, icon) in enumerate(modules):
            r = idx // 3
            col = idx % 3

            cell = tk.Frame(grid, bg=BG_CARD, bd=2, relief="flat",
                            highlightthickness=2, highlightbackground=color,
                            cursor="hand2", padx=8, pady=6)
            cell.grid(row=r, column=col, padx=10, pady=6, sticky="nsew")

            tk.Label(cell, text=icon, font=("Segoe UI Emoji", 18), bg=BG_CARD).pack(pady=(2, 0))
            tk.Label(cell, text=title, font=FONT_HEADER, bg=BG_CARD, fg=color, justify="center").pack(pady=2)
            tk.Label(cell, text=desc, font=FONT_SMALL, bg=BG_CARD, fg=TEXT_WHITE, justify="center").pack(pady=(0, 2))

            btn = neon_button(cell, "▶ LAUNCH MODULE", lambda k=key: self.navigate(k), color=color, width=16)
            btn.pack(pady=(4, 2))

            cell.bind("<Button-1>", lambda e, k=key: self.navigate(k))
            self.cards.append((cell, color))

        for c in range(3):
            grid.columnconfigure(c, weight=1)
        for row_ in range(2):
            grid.rowconfigure(row_, weight=1)

        # Status footer
        footer = tk.Label(self, text="● IPC & SYNCHRONIZATION ARCADE SUITE v2.0 ● 6 MODULES INTEGRATED ●",
                          font=FONT_SMALL, bg=BG_PANEL, fg=NEON_GREEN, pady=3)
        footer.pack(fill="x", side="bottom")

    def _draw_banner(self):
        c = self.tc
        c.delete("all")
        w = c.winfo_width() if c.winfo_width() > 10 else 1000

        # Title
        title = "IPC & SYNCHRONIZATION ARCADE"
        c.create_text(w // 2 + 2, 32, text=title, font=FONT_TITLE, fill="#222244")
        c.create_text(w // 2, 30, text=title, font=FONT_TITLE, fill=NEON_YELLOW)

        # Pac-Man animated on left
        self._mouth += 4 * self._mouth_dir
        if self._mouth >= 50 or self._mouth <= 2:
            self._mouth_dir *= -1
        draw_pacman(c, 70, 32, r=26, mouth_angle=self._mouth, color=NEON_YELLOW, tag="mm_pac")

        # Ghost on right
        draw_ghost(c, w - 70, 32, r=24, color=NEON_PINK, tag="mm_ghost")

        # Dots in between
        for i in range(7):
            dx = 115 + i * 20
            dy = 32 + math.sin((self._tick + i * 2) * 0.2) * 3
            c.create_oval(dx - 3, dy - 3, dx + 3, dy + 3, fill=NEON_YELLOW, outline="")

    def on_show(self):
        self._animate()

    def on_hide(self):
        if self._anim_id:
            self.after_cancel(self._anim_id)
            self._anim_id = None

    def _animate(self):
        self._tick += 1
        self._draw_banner()
        self._anim_id = self.after(70, self._animate)


# ─────────────────────────────────────────────────────────────────────────────
# 12. NAVIGATION TOP BAR
# ─────────────────────────────────────────────────────────────────────────────

class TopBar(tk.Frame):
    """Unified top navigation bar with dropdown, home button, audio toggle, and clock."""

    def __init__(self, parent, navigate_cb):
        super().__init__(parent, bg=BG_PANEL, pady=4)
        self.navigate = navigate_cb
        self._build_ui()

    def _build_ui(self):
        # Home button
        home_btn = tk.Button(
            self, text="👾 IPC ARCADE", font=("Courier New", 13, "bold"),
            bg=BG_PANEL, fg=NEON_YELLOW, relief="flat", bd=0, cursor="hand2",
            activebackground=BG_PANEL, activeforeground=NEON_ORANGE,
            command=lambda: self.navigate("home"), padx=10
        )
        home_btn.pack(side="left")

        sep = tk.Frame(self, bg=NEON_YELLOW, width=2)
        sep.pack(side="left", fill="y", padx=8, pady=2)

        # Module dropdown selector
        tk.Label(self, text="MODULE:", font=FONT_SMALL, bg=BG_PANEL, fg=TEXT_DIM).pack(side="left", padx=(4, 2))
        self.mod_var = tk.StringVar(value="Home Dashboard")
        self.modules_map = {
            "Home Dashboard": "home",
            "Module 1: IPC & Synchronization": "ipc_sync",
            "Module 2: CPU Scheduling": "cpu_sched",
            "Module 3: Memory Management": "mem_mgmt",
            "Module 4: Deadlock & Philosophers": "deadlock",
            "Module 5: File Systems": "file_sys",
            "Module 6: Process Management": "proc_mgmt",
        }
        om = tk.OptionMenu(self, self.mod_var, *self.modules_map.keys(), command=self._on_select)
        om.config(bg=BG_CARD, fg=NEON_BLUE, font=FONT_SMALL, bd=0, relief="flat",
                  highlightthickness=1, highlightbackground=NEON_BLUE)
        om["menu"].config(bg=BG_CARD, fg=NEON_BLUE, font=FONT_SMALL)
        om.pack(side="left", padx=4)

        # Current Module Status
        self.cur_label = tk.Label(self, text="▶ HOME DASHBOARD", font=FONT_SMALL, bg=BG_PANEL, fg=NEON_GREEN)
        self.cur_label.pack(side="left", padx=12)

        # Audio Toggle Button
        self.btn_audio = tk.Button(
            self, text="🔊 AUDIO: ON", font=FONT_SMALL, bg=BG_CARD, fg=NEON_GREEN,
            relief="flat", bd=0, padx=8, pady=2, cursor="hand2",
            command=self._toggle_audio
        )
        self.btn_audio.pack(side="right", padx=10)

        # Arcade clock
        self.clock = tk.Label(self, text="", font=FONT_SMALL, bg=BG_PANEL, fg=TEXT_DIM)
        self.clock.pack(side="right", padx=10)
        self._tick_clock()

    def _on_select(self, choice: str):
        key = self.modules_map.get(choice, "home")
        self.navigate(key)

    def set_current(self, name: str):
        self.cur_label.config(text=f"▶ {name.upper()}")
        for k, v in self.modules_map.items():
            if v == name or k == name:
                self.mod_var.set(k)
                break

    def _toggle_audio(self):
        state = SOUND_ENGINE.toggle()
        if state:
            self.btn_audio.config(text="🔊 AUDIO: ON", fg=NEON_GREEN)
            SOUND_ENGINE.play_send()
        else:
            self.btn_audio.config(text="🔇 AUDIO: OFF", fg=TEXT_DIM)

    def destroy(self):
        if hasattr(self, '_clock_id') and self._clock_id:
            try:
                self.after_cancel(self._clock_id)
            except Exception:
                pass
        super().destroy()

    def _tick_clock(self):
        try:
            if not self.winfo_exists():
                return
            self.clock.config(text=datetime.now().strftime("🕐 %H:%M:%S"))
            self._clock_id = self.after(1000, self._tick_clock)
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# 13. INTEGRATED APPLICATION RUNNER
# ─────────────────────────────────────────────────────────────────────────────

class IPCSyncApp:
    """Master application controller orchestrating all 6 modules."""

    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("IPC & SYNC ARCADE — Unified Operating Systems Simulation Suite")
        
        # Responsive, screen-aware geometry (fits 1366x768, 1080p, and above)
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        target_w = min(1260, max(960, sw - 40))
        target_h = min(680, max(520, sh - 75))
        pos_x = max(0, (sw - target_w) // 2)
        pos_y = max(0, (sh - target_h) // 2 - 20)
        root.geometry(f"{target_w}x{target_h}+{pos_x}+{pos_y}")
        root.minsize(min(960, sw - 20), min(500, sh - 60))
        root.configure(bg=BG_DARK)

        self.frames = {}
        self.current_key = None

        self._build_app()
        self._navigate("home")

    def _build_app(self):
        # Top Navigation Bar
        self.topbar = TopBar(self.root, self._navigate)
        self.topbar.pack(fill="x", side="top")

        sep = tk.Frame(self.root, bg=NEON_YELLOW, height=2)
        sep.pack(fill="x", side="top")

        # Container for all module frames
        self.content = tk.Frame(self.root, bg=BG_DARK)
        self.content.pack(fill="both", expand=True)

        # Instantiate all 6 modules + Home Dashboard
        self.frames["home"] = MainMenuFrame(self.content, self._navigate)
        self.frames["ipc_sync"] = IPCSyncModule(self.content, notify_home_cb=lambda: self._navigate("home"))
        self.frames["cpu_sched"] = CPUSchedulingModule(self.content)
        self.frames["mem_mgmt"] = MemoryManagementModule(self.content)
        self.frames["deadlock"] = DeadlockModule(self.content)
        self.frames["file_sys"] = FileSystemsModule(self.content)
        self.frames["proc_mgmt"] = ProcessManagementModule(self.content)

        # Pre-place frames
        for frame in self.frames.values():
            frame.place(relx=0, rely=0, relwidth=1, relheight=1)
            frame.lower()

        # Keyboard shortcuts
        self.root.bind("<Control-h>", lambda e: self._navigate("home"))
        self.root.bind("<Control-1>", lambda e: self._navigate("ipc_sync"))
        self.root.bind("<Control-2>", lambda e: self._navigate("cpu_sched"))
        self.root.bind("<Control-3>", lambda e: self._navigate("mem_mgmt"))
        self.root.bind("<Control-4>", lambda e: self._navigate("deadlock"))
        self.root.bind("<Control-5>", lambda e: self._navigate("file_sys"))
        self.root.bind("<Control-6>", lambda e: self._navigate("proc_mgmt"))

    def _navigate(self, key: str):
        if key == self.current_key:
            return

        # Hide old
        if self.current_key and self.current_key in self.frames:
            old = self.frames[self.current_key]
            if hasattr(old, "on_hide"):
                old.on_hide()
            old.lower()

        # Show new
        self.current_key = key
        frame = self.frames.get(key)
        if frame:
            frame.lift()
            if hasattr(frame, "on_show"):
                frame.on_show()

        # Update TopBar label
        names = {
            "home": "Home Dashboard",
            "ipc_sync": "Module 1: IPC & Synchronization",
            "cpu_sched": "Module 2: CPU Scheduling",
            "mem_mgmt": "Module 3: Memory Management",
            "deadlock": "Module 4: Deadlock & Philosophers",
            "file_sys": "Module 5: File Systems",
            "proc_mgmt": "Module 6: Process Management",
        }
        self.topbar.set_current(names.get(key, key))


# ─────────────────────────────────────────────────────────────────────────────
# 14. PROGRAM ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def main():
    import sys
    import traceback

    # 1. Safely set High DPI scaling on Windows BEFORE creating the window
    try:
        from ctypes import windll
        try:
            windll.user32.SetProcessDpiAwarenessContext(-4)
        except Exception:
            windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    try:
        root = tk.Tk()

        # Route any unexpected Tkinter background callback error to console/log
        def on_tk_exception(exc, val, tb):
            err_text = "".join(traceback.format_exception(exc, val, tb))
            print("[TKINTER CALLBACK ERROR]:\n", err_text, file=sys.stderr)
            try:
                with open("crash_log.txt", "a", encoding="utf-8") as f:
                    f.write(f"\n--- {datetime.now()} ---\n{err_text}\n")
            except Exception:
                pass

        tk.Tk.report_callback_exception = lambda self, exc, val, tb: on_tk_exception(exc, val, tb)

        app = IPCSyncApp(root)
        root.mainloop()

    except Exception as e:
        err_msg = traceback.format_exc()
        print("[FATAL APPLICATION ERROR]:\n", err_msg, file=sys.stderr)
        try:
            with open("crash_log.txt", "w", encoding="utf-8") as f:
                f.write(f"Fatal Startup Error at {datetime.now()}:\n\n{err_msg}")
        except Exception:
            pass
        try:
            import tkinter.messagebox as mb
            mb.showerror("IPC Arcade - Launch Error",
                         f"A startup error occurred:\n\n{err_msg}\n\nDetails saved to crash_log.txt")
        except Exception:
            pass


if __name__ == "__main__":
    main()
