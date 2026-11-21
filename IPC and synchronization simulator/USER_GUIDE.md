# USER GUIDE: IPC & SYNCHRONIZATION ARCADE
**Pac-Man Themed Operating Systems Educational Simulator**  
**Version:** 2.0  

---

## 1. Quick Start Guide

### Prerequisites
- Python 3.8 or newer (tested on Python 3.10, 3.11, 3.12, 3.13, and 3.14).
- Windows, macOS, or Linux.
- **Zero external libraries required** — runs entirely on standard Python (`tkinter`, `threading`, `time`, `math`, `random`, `winsound`).

### Launching the Application

**Option 1: Double-Click Launcher (Easiest)**
Double-click `run.bat` in the project folder, or run:
```powershell
.\run.bat
```

**Option 2: Run via Terminal Command**
```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe" ipc_simulator.py
```
*(or `python ipc_simulator.py` if Python is added to your PATH)*.

---

## 2. Interface Overview

The simulator interface is divided into four main sections:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 👾 IPC ARCADE | MODULE: [Dropdown Menu ▼] | 🔊 AUDIO: ON | 🕐 15:30:00       │  <-- TOP NAV BAR
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  [🕹️ ARENA]   [🏆 CHALLENGE MISSIONS]   [🧠 QUIZ BATTLE]   [📖 OS GUIDE]    │  <-- SUB-TABS
├───────────────────┬─────────────────────────────────────┬───────────────────┤
│                   │                                     │                   │
│  CONTROLS         │  SIMULATION ARENA CANVAS            │  SEMAPHORES       │
│  • Message Input  │  • Pac-Man (Producer)               │  • Mutex [1/0]    │
│  • Quick Presets  │  • Conduit Tubes                    │  • Empty [N]      │
│  • Send / Recv    │  • Bounded Mailbox Slots            │  • Full  [0]      │
│  • Auto-Produce   │  • Ghost (Consumer)                 │                   │
│  • Auto-Consume   │  • In/Out Pointers                  │  PACKET INSPECTOR │
│  • Buffer Size    ├─────────────────────────────────────┤  • ID, Sender     │
│                   │  SYNCHRONIZATION TRACER             │  • Payload, Size  │
│                   ├─────────────────────────────────────┤                   │
│                   │  TERMINAL KERNEL LOG                │                   │
└───────────────────┴─────────────────────────────────────┴───────────────────┘
```

---

## 3. Using Module 1: IPC & Synchronization

### 3.1 Sub-Tab 1: Simulation Arena (`🕹️ ARENA`)

#### Manual Message Passing:
1. **Choose IPC Model:** Select either **Mailbox (Indirect)** or **Direct Message Passing** from the dropdown menu.
2. **Enter Message Payload:** Type any custom message into the **Message Payload** field, or click any of the **Quick Presets** (`🟡 Power Pellet`, `🍒 Bonus Cherry`, `🍓 Strawberry`, `⚡ Speed Pulse`, `📡 Radar Signal`, `🔑 Secret Key`).
3. **Select Target Receiver:** Choose which ghost consumer to target (`Blinky`, `Pinky`, `Inky`, or `Clyde`).
4. **Dispatch Message (Send):** Click the yellow **▶ SEND (PROC-A)** button.
   - Pac-Man chomps and dispatches a glowing packet through the conduit tube.
   - The tracer highlights `wait(empty)` $\rightarrow$ `wait(mutex)` $\rightarrow$ `buffer.put()` $\rightarrow$ `signal(mutex)` $\rightarrow$ `signal(full)`.
   - The packet settles into the first available mailbox slot.
   - The `EMPTY` semaphore decrements by 1; `FULL` semaphore increments by 1.
5. **Consume Message (Receive):** Click the blue **◀ RECEIVE (PROC-B)** button.
   - The ghost dequeues the oldest message in FIFO order.
   - The tracer highlights `wait(full)` $\rightarrow$ `wait(mutex)` $\rightarrow$ `buffer.get()` $\rightarrow$ `signal(mutex)` $\rightarrow$ `signal(empty)`.
   - The message packet travels to the ghost and is consumed.

#### Testing Bounded Buffer Overflow (Backpressure):
1. Repeatedly click **▶ SEND** until all mailbox slots are filled ($N/N$).
2. Click **▶ SEND** once more.
3. Observe:
   - Pac-Man turns red and displays `[BLOCKED]`.
   - The warning banner announces: `⚠ BUFFER FULL! Producer blocked on wait(empty)`.
   - The warning buzzer sounds.
   - The pseudocode tracer highlights `wait(empty)` in red to demonstrate the condition synchronization block.
4. Click **◀ RECEIVE** once. The consumer frees a slot, signaling `empty`, which instantly unblocks Pac-Man back to `[RUNNING]`!

#### Testing Consumer Starvation:
1. Click **↺ RESET BUFFER** to empty all slots ($0/N$).
2. Click **◀ RECEIVE (PROC-B)**.
3. Observe:
   - The Ghost turns scared blue/red and displays `[BLOCKED]`.
   - The warning banner announces: `⚠ BUFFER EMPTY! Consumer blocked on wait(full)`.
   - The pseudocode tracer highlights `wait(full)` in red.
4. Click **▶ SEND**. A new pellet arrives, signaling `full`, which instantly unblocks the ghost back to `[RUNNING]`!

#### Automated Simulation (Producer-Consumer Rate Generator):
1. Click **⚡ AUTO-PRODUCE: OFF** to toggle it **ON**. Pac-Man will automatically generate and dispatch messages at the specified interval.
2. Click **⚡ AUTO-CONSUME: OFF** to toggle it **ON**. The Ghost will automatically dequeue messages at its specified interval.
3. **Experiment with Rate Mismatches:**
   - **Fast Producer / Slow Consumer:** Set Producer to `0.5s` and Consumer to `2.0s`. Watch the buffer steadily fill up until backpressure suspends Pac-Man!
   - **Slow Producer / Fast Consumer:** Set Producer to `2.5s` and Consumer to `0.5s`. Watch the buffer drain until consumer starvation blocks the Ghost!

#### Inspecting Packet Details:
Click on any occupied slot inside the Mailbox Buffer on the canvas. The **[ PACKET INSPECTOR ]** panel on the right will instantly display the packet's full metadata:
- Unique Packet ID
- Sender Moniker & PID
- Receiver Moniker & PID
- Kernel Timestamp
- Payload String
- Total Packet Size in Bytes

---

### 3.2 Sub-Tab 2: Challenge Missions (`🏆 CHALLENGE MISSIONS`)

Master OS IPC concepts by completing four structured laboratory missions:

- **Mission 1: The First Handshake**  
  *Goal:* Successfully dispatch and receive 3 messages through the mailbox.  
  *Points:* +2,500 pts.
- **Mission 2: The Bounded Overflow Test**  
  *Goal:* Fill the mailbox buffer to 100% capacity to trigger a producer overflow block.  
  *Points:* +2,500 pts.
- **Mission 3: Ghost Starvation Rescue**  
  *Goal:* Drain the buffer until the consumer enters the `BLOCKED` state, then dispatch a message to rescue it.  
  *Points:* +2,500 pts.
- **Mission 4: Dynamic Rate Balancing**  
  *Goal:* Turn ON both Auto-Produce and Auto-Consume. Adjust their sliders to keep buffer occupancy between 30% and 70% for 5 continuous seconds!  
  *Points:* +2,500 pts.

As you complete missions, your **Arcade Score** increases and your rank advances from **Novice Kernel** all the way to **Master of Kernel**!

---

### 3.3 Sub-Tab 3: Arcade Quiz Battle (`🧠 QUIZ BATTLE`)

Test your knowledge with 5 multiple-choice questions on Operating System concepts:
- Click your chosen answer.
- Receive instant feedback and detailed explanations.
- Correct answers award points, play fanfare chimes, and advance Pac-Man across the dot trail towards a bonus cherry fruit!
- Click **RETAKE QUIZ** at any time to try for a 100% score.

---

### 3.4 Sub-Tab 4: Concept Guide (`📖 OS GUIDE`)

Read the complete textbook reference covering:
- What is IPC?
- Shared Memory vs. Message Passing
- Direct vs. Indirect Communication
- The Bounded Buffer Problem
- Dijkstra's Three-Semaphore Solution
- Real-world OS analogs (UNIX pipes, POSIX queues, Windows ALPC)

---

## 4. Exploring the Integrated Modules (Modules 2 to 6)

Use the top dropdown menu or click **👾 IPC ARCADE** to return to the Dashboard and launch any companion module:

### Module 2: CPU Scheduling Arcade
- Choose between **Round Robin (RR)**, **FCFS**, and **Shortest Job First (SJF)**.
- Adjust the Time Quantum slider.
- Click **▶ RUN SIMULATION** or **⏯ STEP FORWARD**.
- Watch the Pac-Man CPU core eat process burst cycles along the live Gantt chart!

### Module 3: Memory Management Arcade
- Enter a process name and required frames (1–6).
- Click **➕ ALLOCATE FRAMES** to allocate memory frames in the physical 4×4 memory matrix.
- Click **➖ DEALLOCATE FIRST** to free frames.
- Observe how the OS handles out-of-memory errors when insufficient frames exist.

### Module 4: Deadlock & Dining Philosophers Arcade
- View the 4 Ghosts sitting around the dining table with 4 power chopsticks.
- Click **⚡ TRIGGER DEADLOCK** to induce Circular Wait where all 4 ghosts hold one fork and wait indefinitely.
- Click **🛡️ DEADLOCK PREVENTION** to apply Dijkstra's resource hierarchy rule and break circular wait!

### Module 5: File Systems & Inodes Arcade
- View the 12-sector circular disk map.
- Click **➕ CREATE GHOST.DAT** to allocate sectors.
- Click **➖ DELETE CHERRY.BMP** to deallocate sectors.
- Click **↺ FORMAT DISK** to wipe and re-index the disk.

### Module 6: Process Management Arcade
- Track a process through the canonical 5 states: `NEW`, `READY`, `RUNNING`, `WAITING`, `TERMINATED`.
- Click **▶ DISPATCH**, **⏸ I/O WAIT**, **✔ I/O DONE**, and **⏹ TERMINATE**.
- Inspect the live **Process Control Block (PCB)** showing PID, PC, Registers, and Memory bounds.

---

## 5. Keyboard Shortcuts

| Shortcut | Action |
| :--- | :--- |
| `Ctrl + H` | Return to Home Dashboard |
| `Ctrl + 1` | Switch to Module 1: IPC & Synchronization |
| `Ctrl + 2` | Switch to Module 2: CPU Scheduling |
| `Ctrl + 3` | Switch to Module 3: Memory Management |
| `Ctrl + 4` | Switch to Module 4: Deadlock & Philosophers |
| `Ctrl + 5` | Switch to Module 5: File Systems |
| `Ctrl + 6` | Switch to Module 6: Process Management |

---

## 6. Running Automated Tests

To run the automated verification test suite:

```powershell
python -m unittest test_ipc_simulator.py -v
```

All 10 test cases will execute and verify FIFO queues, semaphores, backpressure, starvation, and GUI integration.
